import polars as pl
from Managers.entry_manager.base_strategy import EntryStrategy

class MomentumExecution(EntryStrategy):
    def __init__(self, momentum_percentage=5.0, indices='NIFTY', base=50):
        """
        Initialize Momentum Execution condition.

        Args:
            momentum_percentage: The momentum percentage threshold (default 5.0%)
            indices: The index name (NIFTY, BANKNIFTY, etc.)
            base: Strike base for calculations (default 50 for NIFTY)
        """
        super().__init__()
        self.momentum_percentage = momentum_percentage
        self.indices = indices
        self.base = base
        self.momentum_execution = False
        self.entry_prices = {}  # Store initial entry prices for each configured leg
        self.leg_configs = {}   # Store leg configurations
        self.initialized = False

    def reset(self):
        """Reset the momentum execution state."""
        self.momentum_execution = False
        self.entry_prices = {}
        self.leg_configs = {}
        self.initialized = False

    def initialize_entry_data(self, order_sequence_mapper, options_extractor, spot_df, current_timestamp):
        """
        Initialize entry prices for all configured legs at entry time.

        Args:
            order_sequence_mapper: OrderSequenceMapper containing leg configurations
            options_extractor: Options data extractor
            spot_df: Spot price dataframe
            current_timestamp: Current timestamp for data fetching
        """
        if not self.initialized and order_sequence_mapper.main_orders:
            for leg_id, leg_config in order_sequence_mapper.main_orders.items():
                try:
                    # Get current spot price
                    spot_price = spot_df.filter(pl.col('Timestamp') == current_timestamp).select('Close').item()

                    # Calculate strike using the standard method
                    strike = self._calculate_strike(leg_config, spot_price)

                    # Get option data using the standard method
                    option_df = self._get_option_row(strike, leg_config, current_timestamp, options_extractor)

                    if not option_df.is_empty():
                        # Store the entry price and leg config
                        close_price = option_df.select('Close').item()
                        self.entry_prices[leg_id] = close_price
                        self.leg_configs[leg_id] = leg_config
                        print(f"Initialized leg {leg_id}: strike={strike}, entry_price={close_price}")

                except Exception as e:
                    print(f"Error initializing leg {leg_id}: {e}")
                    continue

            self.initialized = True
            print(f"Momentum execution initialized with {len(self.entry_prices)} legs")

    def check_momentum_condition(self, current_time, spot_df, options_extractor, order_sequence_mapper, entry_para_dict):
        """
        Check if momentum condition is met for re-execution.

        Args:
            current_time: Current timestamp
            spot_df: Spot price dataframe
            options_extractor: Options data extractor
            order_sequence_mapper: OrderSequenceMapper containing leg configurations
            entry_para_dict: Entry parameters dictionary

        Returns:
            bool: True if momentum condition is met, False otherwise
        """
        if not self.initialized or not self.entry_prices:
            return False

        try:
            # Get current spot price
            current_spot = spot_df.filter(pl.col('Timestamp') == current_time).select('Close').item()

            # Check if ALL legs have dropped below the momentum threshold
            all_legs_below_threshold = True

            for leg_id, initial_price in self.entry_prices.items():
                try:
                    # Calculate current strike using the standard method
                    current_strike = self._calculate_strike(self.leg_configs[leg_id], current_spot)

                    # Get current option data using the standard method
                    current_option_df = self._get_option_row(current_strike, self.leg_configs[leg_id], current_time, options_extractor)

                    if not current_option_df.is_empty():
                        current_price = current_option_df.select('Close').item()

                        # Calculate percentage change
                        price_change = ((initial_price - current_price) / initial_price) * 100

                        print(f"Leg {leg_id}: initial={initial_price:.2f}, current={current_price:.2f}, change={price_change:.2f}%")

                        # Check if this leg is below threshold
                        if price_change < self.momentum_percentage:
                            all_legs_below_threshold = False
                            break
                    else:
                        # If we can't get current data, assume condition not met
                        all_legs_below_threshold = False
                        break

                except Exception as e:
                    print(f"Error checking leg {leg_id}: {e}")
                    all_legs_below_threshold = False
                    break

            if all_legs_below_threshold:
                print(f"Momentum condition met! All legs dropped >= {self.momentum_percentage}%")
                self.momentum_execution = True
                return True

        except Exception as e:
            print(f"Error in momentum check: {e}")

        return False

    def get_re_execution_params(self, entry_para_dict):
        """
        Get modified parameters for re-execution.

        Args:
            entry_para_dict: Original entry parameters

        Returns:
            dict: Modified parameters for re-execution
        """
        # Create a copy of entry parameters with modified SL and target
        re_execute_params = entry_para_dict.copy()

        # Modify stop loss and target for re-execution (example: tighter SL, higher target)
        if 're_execute_sl' in entry_para_dict:
            re_execute_params['stoploss_value'] = entry_para_dict['re_execute_sl']
        if 're_execute_target' in entry_para_dict:
            re_execute_params['target_value'] = entry_para_dict['re_execute_target']

        return re_execute_params

    def _calculate_strike(self, leg_config, spot_price):
        """
        Calculate strike price based on strike_type.
        Copied from base_strategy.py for consistency.

        Args:
            leg_config: Leg configuration
            spot_price: Current spot price

        Returns:
            Calculated strike price
        """
        strike_type = leg_config.get('strike_type', 'ATM')

        if strike_type == 'ATM':
            return self.base * round(spot_price / self.base)

        elif strike_type == 'OTM':
            spread_value = leg_config.get('spread', 0) * self.base
            if leg_config.get('option_type') == 'CE':
                return self.base * round((spot_price + spread_value) / self.base)
            else:  # PE
                return self.base * round((spot_price - spread_value) / self.base)

        elif strike_type == 'ITM':
            spread_value = leg_config.get('spread', 0) * self.base
            if leg_config.get('option_type') == 'CE':
                return self.base * round((spot_price - spread_value) / self.base)
            else:  # PE
                return self.base * round((spot_price + spread_value) / self.base)

        else:
            # Default to ATM
            return self.base * round(spot_price / self.base)

    def _get_option_row(self, strike, leg_config, timestamp, options_extractor):
        """
        Get option data for specific strike and timestamp.
        Copied from base_strategy.py for consistency.

        Args:
            strike: Strike price
            leg_config: Leg configuration
            timestamp: Timestamp to fetch data for
            options_extractor: Options data extractor

        Returns:
            Polars DataFrame with option data, or None if not found
        """
        try:
            df = options_extractor.data_handler.get_option_data(
                timestamp=timestamp,
                strike=strike,
                option_type=leg_config['option_type'],
                expiry_type=leg_config['expiry_type']
            )

            # Filter for specific instrument type and timestamp
            if not df.is_empty():
                filtered = df.filter(
                    (pl.col('Strike') == strike) &
                    (pl.col('Instrument_type') == leg_config['option_type'])
                )
                return filtered if not filtered.is_empty() else None
            return None

        except Exception as e:
            print(f"Error fetching option data: {e}")
            return None