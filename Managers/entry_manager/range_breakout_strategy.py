"""
Range Breakout Entry Strategy

Waits for price to break out of a defined range before executing.
Supports:
- High breakout (price goes above range high)
- Low breakout (price goes below range low)
- Configurable range calculation period
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, time as dt_time
import polars as pl

from .base_strategy import EntryStrategy, OrderSpec


class RangeBreakoutStrategy(EntryStrategy):
    """
    Strategy for range breakout order execution.
    
    This strategy:
    1. Calculates range (high/low) during specified period
    2. Waits for price to break out of range
    3. Executes when breakout occurs
    """
    
    def generate_order_spec(
        self,
        leg_id: str,
        leg_config: Dict[str, Any],
        timestamp: datetime,
        spot_price: float
    ) -> Optional[OrderSpec]:
        """
        Generate order spec with range breakout threshold.
        
        Strategy Data Fields:
        - ticker: Trading symbol
        - strike: Calculated strike price
        - range_break_price: High or Low of range
        - breakout_direction: 'ABOVE' or 'BELOW'
        - range_start: Range calculation start time
        - range_end: Range calculation end time
        - compare_field: Field to compare (Close, High, Low)
        - ready_to_execute: False (waiting for range calculation)
        """
        try:
            # Get range threshold time
            threshold_time_str = leg_config.get('range_breakout_threshold_time', '15:30:00')
            threshold_time = datetime.strptime(threshold_time_str, "%H:%M:%S").time()
            
            # Check if we're still in range calculation period
            if timestamp.time() >= threshold_time:
                self._log(
                    f"Range calculation period already passed for {leg_id}",
                    'warning'
                )
                return None
            
            # Calculate strike
            strike = self._calculate_strike(leg_config, spot_price)
            
            # Get option data
            option_df = self._get_option_row(strike, leg_config, timestamp)
            
            if option_df is None or option_df.height == 0:
                self._log(
                    f"No option data for range breakout strike {strike} at {timestamp}",
                    'warning'
                )
                return None
            
            # Store ticker for later range calculation
            row_dict = option_df.row(0, named=True)
            ticker = row_dict['Ticker']
            
            # Determine breakout direction
            breakout_of = leg_config.get('range_breakout_of', 'High')
            breakout_direction = 'ABOVE' if breakout_of == 'High' else 'BELOW'
            
            # Build strategy data (range will be calculated later when threshold time reached)
            strategy_data = {
                'ticker': ticker,
                'strike': strike,
                'instrument_type': row_dict['Instrument_type'],
                'range_break_price': None,  # Will be calculated when range period ends
                'breakout_direction': breakout_direction,
                'breakout_of': breakout_of,  # 'High' or 'Low'
                'range_start': timestamp,
                'range_end': threshold_time,
                'compare_field': leg_config.get('range_compare_section', 'Close'),
                'expiry': str(row_dict['Expiry']),
                'range_calculated': False,
                'ready_to_execute': False
            }
            
            # Create order spec
            order_spec = OrderSpec(
                order_id=f"{leg_id}_{int(timestamp.timestamp())}",
                leg_id=leg_id,
                leg_config=leg_config,
                timestamp_created=timestamp,
                strategy_type='RANGE_BREAKOUT',
                strategy_data=strategy_data
            )
            
            self._log(
                f"Generated range breakout order for {leg_id}: "
                f"Strike={strike}, Breakout={breakout_direction} {breakout_of}, "
                f"Range period: {timestamp.time()} to {threshold_time}"
            )
            
            return order_spec
            
        except Exception as e:
            self._log(f"Error generating range breakout order: {e}", 'error')
            return None
    
    def _calculate_range(
        self,
        order_spec: OrderSpec,
        timestamp: datetime
    ) -> Optional[float]:
        """
        Calculate range breakout level.
        
        This is called when threshold time is reached.
        
        Returns:
            Range breakout price (high or low of range period)
        """
        try:
            data = order_spec.strategy_data
            leg_config = order_spec.leg_config
            
            # Get all data from range start to threshold time
            # We need to fetch the full day's data and filter
            full_day_df = self.options_extractor.data_handler(
                strike_price=None,
                expiry_type=leg_config['leg_expiry_selection'],
                current_timestamp=timestamp,
                indices=self.indices,
                ticker=data['ticker']
            )
            
            if full_day_df is None or full_day_df.height == 0:
                return None
            
            # Filter for range period
            range_start_time = data['range_start'].time()
            range_end_time = data['range_end']
            
            range_df = full_day_df.filter(
                (pl.col('Timestamp').dt.time() >= range_start_time) &
                (pl.col('Timestamp').dt.time() <= range_end_time)
            )
            
            if range_df.height == 0:
                return None
            
            # Calculate range breakout level
            if data['breakout_of'] == 'High':
                range_break_price = range_df.select('High').max().item()
            else:  # Low
                range_break_price = range_df.select('Low').min().item()
            
            return round(range_break_price, 2)
            
        except Exception as e:
            self._log(f"Error calculating range: {e}", 'error')
            return None
    
    def can_execute(
        self,
        order_spec: OrderSpec,
        timestamp: datetime,
        spot_price: float
    ) -> bool:
        """
        Check if price has broken out of range.
        
        Returns:
            True if breakout occurred, False otherwise
        """
        try:
            data = order_spec.strategy_data
            
            # First, check if we need to calculate range
            if not data['range_calculated']:
                # Check if threshold time reached
                if timestamp.time() > data['range_end']:
                    # Calculate range now
                    range_price = self._calculate_range(order_spec, timestamp)
                    
                    if range_price is None:
                        self._log(
                            f"Could not calculate range for {order_spec.leg_id}",
                            'warning'
                        )
                        return False
                    
                    # Update strategy data
                    data['range_break_price'] = range_price
                    data['range_calculated'] = True
                    
                    self._log(
                        f"Range calculated for {order_spec.leg_id}: "
                        f"{data['breakout_of']}={range_price:.2f}"
                    )
                else:
                    # Still in range calculation period
                    return False
            
            # Now check for breakout
            if data['range_break_price'] is None:
                return False
            
            # Get current option price
            option_df = self._get_option_by_ticker(
                ticker=data['ticker'],
                leg_config=order_spec.leg_config,
                timestamp=timestamp
            )
            
            if option_df is None or option_df.height == 0:
                return False
            
            row_dict = option_df.row(0, named=True)
            current_value = row_dict[data['compare_field']]
            range_break_price = data['range_break_price']
            
            # Check breakout
            if data['breakout_direction'] == 'ABOVE':
                breakout = current_value > range_break_price
            else:  # BELOW
                breakout = current_value < range_break_price
            
            if breakout:
                self._log(
                    f"Range breakout for {order_spec.leg_id}: "
                    f"Current={current_value:.2f}, Range={range_break_price:.2f}, "
                    f"Direction={data['breakout_direction']}"
                )
            
            return breakout
            
        except Exception as e:
            self._log(f"Error checking range breakout: {e}", 'error')
            return False
    
    def execute(
        self,
        order_spec: OrderSpec,
        timestamp: datetime,
        spot_price: float,
        TRADE_DICT: Dict[str, list],
        order_book: Dict[str, list]
    ) -> Tuple[Dict[str, list], Dict[str, list]]:
        """
        Execute range breakout entry.
        """
        try:
            data = order_spec.strategy_data
            leg_config = order_spec.leg_config
            
            # Get current option data for execution
            option_df = self._get_option_by_ticker(
                ticker=data['ticker'],
                leg_config=leg_config,
                timestamp=timestamp
            )
            
            if option_df is None or option_df.height == 0:
                raise ValueError(f"No option data at execution for {data['ticker']}")
            
            row_dict = option_df.row(0, named=True)
            
            # Determine entry price
            actual_entry_price = round(row_dict[self.entry_mode], 2)
            
            # Calculate SL and Target
            position_type = leg_config.get('position', 'Sell')
            stop_loss, target_price = self._calculate_sl_target(
                entry_price=actual_entry_price,
                leg_config=leg_config,
                position_type=position_type
            )
            
            # Calculate P&L (initial)
            current_close = row_dict['Close']
            if position_type == 'Sell':
                pnl = (actual_entry_price - current_close) * (self.lot_qty * self.lotsize)
            else:  # Buy
                pnl = (current_close - actual_entry_price) * (self.lot_qty * self.lotsize)
            
            # Update TRADE_DICT
            TRADE_DICT['Leg_id'].append(order_spec.leg_id)
            TRADE_DICT['Entry_timestamp'].append(timestamp)
            TRADE_DICT['Timestamp'].append(timestamp)
            TRADE_DICT['TradingSymbol'].append(data['ticker'])
            TRADE_DICT['Instrument_type'].append(data['instrument_type'])
            TRADE_DICT['Entry_price'].append(actual_entry_price)
            TRADE_DICT['LTP'].append(round(current_close, 2))
            TRADE_DICT['Position_type'].append(position_type)
            TRADE_DICT['Strike'].append(data['strike'])
            TRADE_DICT['Stop_loss'].append(stop_loss)
            TRADE_DICT['Target_price'].append(target_price)
            TRADE_DICT['Lot_size'].append(self.lot_qty)
            TRADE_DICT['Expiry_type'].append(leg_config['leg_expiry_selection'])
            TRADE_DICT['PnL'].append(round(pnl, 2))
            
            # Add trailing if enabled
            trailing_value = actual_entry_price if leg_config.get('trail_sl_toggle') else 0
            TRADE_DICT['Trailing'].append(trailing_value)
            
            # Update order_book
            summary = (
                f"Range breakout entry @ {actual_entry_price} "
                f"(Range {data['breakout_of']}: {data['range_break_price']}, "
                f"Breakout {data['breakout_direction']}, "
                f"SL: {'NA' if stop_loss == 0 else stop_loss}, "
                f"Target: {'NA' if target_price == 0 else target_price})"
            )
            
            order_book['Timestamp'].append(timestamp)
            order_book['Ticker'].append(data['ticker'])
            order_book['Price'].append(actual_entry_price)
            order_book['Order_side'].append(position_type)
            order_book['Summary'].append(summary)
            
            self._log(
                f"Executed range breakout entry for {order_spec.leg_id}: "
                f"{data['ticker']} @ {actual_entry_price}"
            )
            
            return TRADE_DICT, order_book
            
        except Exception as e:
            self._log(f"Error executing range breakout entry: {e}", 'error')
            raise