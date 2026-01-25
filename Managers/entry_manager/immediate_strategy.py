"""
Immediate Entry Strategy

Executes orders immediately when submitted.
No waiting for conditions - entry happens right away.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import polars as pl

from .base_strategy import EntryStrategy, OrderSpec


class ImmediateEntryStrategy(EntryStrategy):
    """
    Strategy for immediate order execution.
    
    This strategy:
    1. Calculates strike and fetches option data during generation
    2. Can always execute (no waiting)
    3. Executes using pre-calculated data
    """
    
    def generate_order_spec(
        self,
        leg_id: str,
        leg_config: Dict[str, Any],
        timestamp: datetime,
        spot_price: float
    ) -> Optional[OrderSpec]:
        """
        Generate order spec with all data for immediate execution.
        
        Strategy Data Fields:
        - strike: Calculated strike price
        - ticker: Trading symbol
        - entry_price: Entry price based on EntryMode
        - instrument_type: CE or PE
        - ohlc: Dict with Open, High, Low, Close
        - ready_to_execute: Always True for immediate
        """
        try:
            # Calculate strike
            strike = self._calculate_strike(leg_config, spot_price)
            
            # Get option data
            option_df = self._get_option_row(strike, leg_config, timestamp)
            
            if option_df is None or option_df.height == 0:
                self._log(
                    f"No option data for strike {strike} at {timestamp}",
                    'warning'
                )
                return None
            
            # Extract row data
            row_dict = option_df.row(0, named=True)
            
            # Build strategy data
            strategy_data = {
                'strike': strike,
                'ticker': row_dict['Ticker'],
                'entry_price': round(row_dict[self.entry_mode], 2),
                'instrument_type': row_dict['Instrument_type'],
                'ohlc': {
                    'open': round(row_dict['Open'], 2),
                    'high': round(row_dict['High'], 2),
                    'low': round(row_dict['Low'], 2),
                    'close': round(row_dict['Close'], 2)
                },
                'expiry': str(row_dict['Expiry']),
                'ready_to_execute': True  # Immediate = always ready
            }
            
            # Create order spec
            order_spec = OrderSpec(
                order_id=f"{leg_id}_{int(timestamp.timestamp())}",
                leg_id=leg_id,
                leg_config=leg_config,
                timestamp_created=timestamp,
                strategy_type='IMMEDIATE',
                strategy_data=strategy_data
            )
            
            self._log(
                f"Generated immediate order for {leg_id}: "
                f"Strike={strike}, Price={strategy_data['entry_price']}"
            )
            
            return order_spec
            
        except Exception as e:
            self._log(f"Error generating immediate order: {e}", 'error')
            return None
    
    def can_execute(
        self,
        order_spec: OrderSpec,
        timestamp: datetime,
        spot_price: float
    ) -> bool:
        """
        Immediate strategy can always execute.
        
        Returns:
            Always True
        """
        return True
    
    def execute(
        self,
        order_spec: OrderSpec,
        timestamp: datetime,
        spot_price: float,
        TRADE_DICT: Dict[str, list],
        order_book: Dict[str, list]
    ) -> Tuple[Dict[str, list], Dict[str, list]]:
        """
        Execute immediate entry using pre-calculated data.
        
        Updates:
        - TRADE_DICT with position details
        - order_book with execution record
        """
        try:
            data = order_spec.strategy_data
            leg_config = order_spec.leg_config
            
            # Calculate stop loss and target
            entry_price = data['entry_price']
            position_type = leg_config.get('position', 'Sell')
            
            stop_loss, target_price = self._calculate_sl_target(
                entry_price=entry_price,
                leg_config=leg_config,
                position_type=position_type
            )
            
            # Calculate P&L (initial)
            if position_type == 'Sell':
                pnl = (entry_price - data['ohlc']['close']) * (self.lot_qty * self.lotsize)
            else:  # Buy
                pnl = (data['ohlc']['close'] - entry_price) * (self.lot_qty * self.lotsize)
            
            # Update TRADE_DICT
            TRADE_DICT['Leg_id'].append(order_spec.leg_id)
            TRADE_DICT['Entry_timestamp'].append(timestamp)
            TRADE_DICT['Timestamp'].append(timestamp)
            TRADE_DICT['TradingSymbol'].append(data['ticker'])
            TRADE_DICT['Instrument_type'].append(data['instrument_type'])
            TRADE_DICT['Entry_price'].append(entry_price)
            TRADE_DICT['LTP'].append(data['ohlc']['close'])
            TRADE_DICT['Position_type'].append(position_type)
            TRADE_DICT['Strike'].append(data['strike'])
            TRADE_DICT['Stop_loss'].append(stop_loss)
            TRADE_DICT['Target_price'].append(target_price)
            TRADE_DICT['Lot_size'].append(self.lot_qty)
            TRADE_DICT['Expiry_type'].append(leg_config['leg_expiry_selection'])
            TRADE_DICT['PnL'].append(round(pnl, 2))
            
            # Add trailing if enabled
            trailing_value = entry_price if leg_config.get('trail_sl_toggle') else 0
            TRADE_DICT['Trailing'].append(trailing_value)
            
            # Update order_book
            summary = (
                f"{data['instrument_type']} Position {position_type}, "
                f"SL: {'NA' if stop_loss == 0 else stop_loss}, "
                f"Target: {'NA' if target_price == 0 else target_price}, "
                f"Trailing: {'NA' if trailing_value == 0 else trailing_value}"
            )
            
            order_book['Timestamp'].append(timestamp)
            order_book['Ticker'].append(data['ticker'])
            order_book['Price'].append(entry_price)
            order_book['Order_side'].append(position_type)
            order_book['Summary'].append(summary)
            
            self._log(
                f"Executed immediate entry for {order_spec.leg_id}: "
                f"{data['ticker']} @ {entry_price}"
            )
            
            return TRADE_DICT, order_book
            
        except Exception as e:
            self._log(f"Error executing immediate entry: {e}", 'error')
            raise