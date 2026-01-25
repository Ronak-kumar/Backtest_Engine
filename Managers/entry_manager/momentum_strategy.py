"""
Momentum Entry Strategy

Waits for price to cross a momentum threshold before executing.
Supports:
- Percentage-based thresholds (up/down)
- Points-based thresholds (up/down)
- Configurable SL/Target calculation basis
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import polars as pl

from .base_strategy import EntryStrategy, OrderSpec


class MomentumEntryStrategy(EntryStrategy):
    """
    Strategy for momentum-based order execution.
    
    This strategy:
    1. Calculates momentum threshold during generation
    2. Waits for price to cross threshold
    3. Executes when threshold is crossed
    """
    
    def generate_order_spec(
        self,
        leg_id: str,
        leg_config: Dict[str, Any],
        timestamp: datetime,
        spot_price: float
    ) -> Optional[OrderSpec]:
        """
        Generate order spec with momentum threshold.
        
        Strategy Data Fields:
        - ticker: Trading symbol
        - strike: Calculated strike price
        - instrument_type: CE or PE
        - normal_entry_price: Entry price at creation
        - momentum_threshold_price: Price threshold to cross
        - direction: PERCENTAGE_UP, PERCENTAGE_DOWN, POINTS_UP, POINTS_DOWN
        - initial_close: Close price at creation
        - sm_tgt_sl_price: Basis for SL/Target (Entry_price, SM_price, System_price)
        - ready_to_execute: False (waiting for threshold)
        """
        try:
            # Calculate strike
            strike = self._calculate_strike(leg_config, spot_price)
            
            # Get option data
            option_df = self._get_option_row(strike, leg_config, timestamp)
            
            if option_df is None or option_df.height == 0:
                self._log(
                    f"No option data for momentum strike {strike} at {timestamp}",
                    'warning'
                )
                return None
            
            # Extract row data
            row_dict = option_df.row(0, named=True)
            
            # Calculate momentum threshold
            current_close = row_dict['Close']
            direction = leg_config.get('sm_percentage_direction', 'PERCENTAGE_UP')
            
            # Get threshold value
            if 'PERCENTAGE' in direction:
                percent_value = leg_config.get('sm_percent_value', 0) / 100
                if direction == 'PERCENTAGE_UP':
                    threshold = current_close + (current_close * percent_value)
                else:  # PERCENTAGE_DOWN
                    threshold = current_close - (current_close * percent_value)
            else:  # POINTS
                point_value = leg_config.get('sm_percent_value', 0)
                if direction == 'POINTS_UP':
                    threshold = current_close + point_value
                else:  # POINTS_DOWN
                    threshold = current_close - point_value
            
            # Build strategy data
            strategy_data = {
                'ticker': row_dict['Ticker'],
                'strike': strike,
                'instrument_type': row_dict['Instrument_type'],
                'normal_entry_price': round(row_dict[self.entry_mode], 2),
                'momentum_threshold_price': round(threshold, 2),
                'direction': direction,
                'initial_close': round(current_close, 2),
                'sm_tgt_sl_price': leg_config.get('sm_tgt_sl_price', 'Entry_price'),
                'expiry': str(row_dict['Expiry']),
                'ready_to_execute': False  # Wait for threshold
            }
            
            # Create order spec
            order_spec = OrderSpec(
                order_id=f"{leg_id}_{int(timestamp.timestamp())}",
                leg_id=leg_id,
                leg_config=leg_config,
                timestamp_created=timestamp,
                strategy_type='MOMENTUM',
                strategy_data=strategy_data
            )
            
            self._log(
                f"Generated momentum order for {leg_id}: "
                f"Strike={strike}, Initial={current_close:.2f}, "
                f"Threshold={threshold:.2f}, Direction={direction}"
            )
            
            return order_spec
            
        except Exception as e:
            self._log(f"Error generating momentum order: {e}", 'error')
            return None
    
    def can_execute(
        self,
        order_spec: OrderSpec,
        timestamp: datetime,
        spot_price: float
    ) -> bool:
        """
        Check if current price has crossed momentum threshold.
        
        Returns:
            True if threshold crossed, False otherwise
        """
        try:
            data = order_spec.strategy_data
            
            # Get current option price
            option_df = self._get_option_by_ticker(
                ticker=data['ticker'],
                leg_config=order_spec.leg_config,
                timestamp=timestamp
            )
            
            if option_df is None or option_df.height == 0:
                return False
            
            # Get current close price
            current_close = option_df.select('Close').item()
            threshold = data['momentum_threshold_price']
            direction = data['direction']
            
            # Check if threshold crossed
            if 'UP' in direction:
                crossed = current_close >= threshold
            else:  # DOWN
                crossed = current_close <= threshold
            
            if crossed:
                self._log(
                    f"Momentum threshold crossed for {order_spec.leg_id}: "
                    f"Current={current_close:.2f}, Threshold={threshold:.2f}"
                )
            
            return crossed
            
        except Exception as e:
            self._log(f"Error checking momentum execution: {e}", 'error')
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
        Execute momentum entry.
        
        Uses sm_tgt_sl_price to determine which price to use for SL/Target:
        - Entry_price: Use actual entry price
        - SM_price: Use momentum threshold price
        - System_price: Use normal entry price (price at creation)
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
            
            # Determine SL/Target calculation basis
            sm_tgt_sl_price = data.get('sm_tgt_sl_price', 'Entry_price')
            
            if sm_tgt_sl_price == 'Entry_price':
                sl_target_base = actual_entry_price
            elif sm_tgt_sl_price == 'SM_price':
                sl_target_base = data['momentum_threshold_price']
            else:  # System_price
                sl_target_base = data['normal_entry_price']
            
            # Calculate SL and Target
            position_type = leg_config.get('position', 'Sell')
            stop_loss, target_price = self._calculate_sl_target(
                entry_price=sl_target_base,
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
                f"Momentum entry @ {actual_entry_price} "
                f"(Threshold: {data['momentum_threshold_price']}, "
                f"SL: {'NA' if stop_loss == 0 else stop_loss}, "
                f"Target: {'NA' if target_price == 0 else target_price})"
            )
            
            order_book['Timestamp'].append(timestamp)
            order_book['Ticker'].append(data['ticker'])
            order_book['Price'].append(actual_entry_price)
            order_book['Order_side'].append(position_type)
            order_book['Summary'].append(summary)
            
            self._log(
                f"Executed momentum entry for {order_spec.leg_id}: "
                f"{data['ticker']} @ {actual_entry_price} "
                f"(Base for SL/Target: {sm_tgt_sl_price}={sl_target_base:.2f})"
            )
            
            return TRADE_DICT, order_book
            
        except Exception as e:
            self._log(f"Error executing momentum entry: {e}", 'error')
            raise