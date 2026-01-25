```markdown
# Entry Manager - Two-Phase Entry System

A robust, scalable entry management system with clear separation between order generation and execution.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Components](#components)
- [Usage Guide](#usage-guide)
- [Adding New Strategies](#adding-new-strategies)
- [Testing](#testing)
- [Migration from Old System](#migration-from-old-system)
- [API Reference](#api-reference)

---

## 🎯 Overview

The Entry Manager implements a **two-phase entry system**:

### **Phase 1: Order Generation**
- Orders are created with all necessary data
- Strategy calculates thresholds, strikes, prices
- Orders stored in pending queue

### **Phase 2: Order Execution**
- Pending orders checked every minute
- Orders execute when conditions met
- Automatic removal from pending queue

### **Benefits**
- ✅ Clean separation of concerns
- ✅ Easy to add new entry strategies
- ✅ Clear execution flow
- ✅ Fully testable
- ✅ Professional architecture

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         EntryManager (Main)              │
│  • submit_order()                        │
│  • execute_pending_entries()             │
│  • pending_orders: Dict[str, OrderSpec]  │
└──────────────┬──────────────────────────┘
               │
               │ Delegates to
               ▼
┌─────────────────────────────────────────┐
│       Strategy Registry                  │
│  {                                       │
│    'IMMEDIATE': ImmediateStrategy(),     │
│    'MOMENTUM': MomentumStrategy(),       │
│    'RANGE_BREAKOUT': RangeBreakoutStrategy()│
│  }                                       │
└─────────────────────────────────────────┘
               │
               │ Each implements
               ▼
┌─────────────────────────────────────────┐
│       EntryStrategy (Base)               │
│  • generate_order_spec()                 │
│  • can_execute()                         │
│  • execute()                             │
└─────────────────────────────────────────┘
```

---

## 📦 Installation

```bash
# Copy the entry_manager_implementation folder to your project
cp -r entry_manager_implementation /path/to/your/project/

# Make sure you have required dependencies
pip install polars --break-system-packages
```

---

## 🚀 Quick Start

### Basic Usage

```python
from entry_manager import EntryManager

# Initialize
entry_manager = EntryManager(
    options_extractor=options_extractor_con,
    spot_df=spot_df,
    config={
        'base': 50,              # Strike base
        'lotsize': 75,           # Lot size
        'lot_qty': 1,            # Number of lots
        'EntryMode': 'Close',    # Entry price mode
        'StoplossCalMode': 'Close',
        'indices': 'NIFTY'
    },
    logger=logger  # Optional
)

# PHASE 1: Submit orders
order_id = entry_manager.submit_order(
    leg_id='leg_1',
    leg_config={
        'unique_leg_id': 'leg_1',
        'strike_type': 'ATM',
        'option_type': 'CE',
        'position': 'Sell',
        'leg_expiry_selection': 'Weekly',
        'stoploss_toggle': True,
        'stoploss_type': 'Percentage',
        'stoploss_value': 0.20
    },
    timestamp=current_time,
    spot_price=20000.0
)

# PHASE 2: Execute pending orders (call every minute)
TRADE_DICT, order_book, executed_ids = entry_manager.execute_pending_entries(
    timestamp=current_time,
    spot_price=spot_price,
    TRADE_DICT=TRADE_DICT,
    order_book=order_book
)

if executed_ids:
    print(f"Executed: {executed_ids}")
```

---

## 📚 Components

### 1. **OrderSpec** (Data Container)

```python
@dataclass
class OrderSpec:
    order_id: str              # Unique ID
    leg_id: str                # Leg identifier
    unique_leg_id: str         # Unique leg ID
    leg_config: dict           # Full leg configuration
    timestamp_created: datetime
    strategy_type: str         # IMMEDIATE, MOMENTUM, etc.
    strategy_data: dict        # Strategy-specific data
```

### 2. **EntryStrategy** (Base Class)

All strategies inherit from this:

```python
class EntryStrategy(ABC):
    def generate_order_spec(...) -> OrderSpec:
        """Generate order with all data"""
    
    def can_execute(...) -> bool:
        """Check if can execute"""
    
    def execute(...) -> (TRADE_DICT, order_book):
        """Execute the order"""
```

### 3. **Concrete Strategies**

#### **ImmediateEntryStrategy**
- Executes immediately when submitted
- No waiting for conditions
- Use for: Normal entries at entry time

#### **MomentumEntryStrategy**
- Waits for price to cross threshold
- Supports: Percentage/Points, Up/Down
- Use for: Momentum-based entries

#### **RangeBreakoutStrategy**
- Waits for price to break range
- Calculates range during specified period
- Use for: Range breakout entries

### 4. **EntryManager** (Orchestrator)

Main class that coordinates everything:

```python
class EntryManager:
    pending_orders: Dict[str, OrderSpec]
    strategy_registry: Dict[str, EntryStrategy]
    executed_orders: List[str]
    
    def submit_order(...) -> str
    def execute_pending_entries(...) -> (TRADE_DICT, order_book, executed_ids)
    def cancel_order(...) -> bool
    def get_statistics() -> dict
    def reset()
```

---

## 📖 Usage Guide

### Integration with Day_Processor

```python
class DayProcessor:
    def __init__(self, ...):
        # Initialize Entry Manager
        self.entry_manager = EntryManager(
            options_extractor=day_option_frame_con,
            spot_df=None,  # Set later
            config={
                'base': entry_para_dict['base_symbol_spread'],
                'lotsize': entry_para_dict['symbol_lotsize'],
                'lot_qty': entry_para_dict['lots'],
                'EntryMode': entry_para_dict['EntryMode'],
                'StoplossCalMode': entry_para_dict['StoplossCalMode'],
                'indices': entry_para_dict['indices']
            }
        )
        self.initial_entry = False
    
    def process_day(self, spot_df, ...):
        # Update spot_df
        self.entry_manager.spot_df = spot_df
        
        for timestamp in spot_df['Timestamp']:
            spot_price = ...
            
            # PHASE 1: Submit orders at entry time
            if current_time >= entry_time and not self.initial_entry:
                for leg_id, leg_config in self.orders.items():
                    order_id = self.entry_manager.submit_order(
                        leg_id, leg_config, timestamp, spot_price
                    )
                self.initial_entry = True
            
            # PHASE 2: Execute pending every minute
            if self.initial_entry:
                TRADE_DICT, order_book, executed = \
                    self.entry_manager.execute_pending_entries(
                        timestamp, spot_price, TRADE_DICT, order_book
                    )
                
                # Create positions for newly executed orders
                for order_id in executed:
                    # Create position in PNL Manager
                    ...
```

### Monitoring Pending Orders

```python
# Get count
pending_count = entry_manager.get_pending_count()
print(f"Pending: {pending_count}")

# Get detailed info
pending_orders = entry_manager.get_pending_orders()
for order_id, order_spec in pending_orders.items():
    print(f"{order_id}: {order_spec.strategy_type}")

# Get statistics
stats = entry_manager.get_statistics()
print(f"Total submitted: {stats['total_submitted']}")
print(f"Executed: {stats['executed_count']}")
print(f"Pending: {stats['pending_count']}")
print(f"By strategy: {stats['pending_by_strategy']}")
```

### Cancelling Orders

```python
# Cancel specific order
success = entry_manager.cancel_order(order_id)

# Cancel all pending
entry_manager.cancel_all_pending()

# Cancel specific strategy type
pending = entry_manager.get_pending_orders()
for order_id, order_spec in pending.items():
    if order_spec.strategy_type == 'MOMENTUM':
        entry_manager.cancel_order(order_id)
```

---

## 🔧 Adding New Strategies

### Step 1: Create Strategy Class

```python
from entry_manager import EntryStrategy, OrderSpec

class MyNewStrategy(EntryStrategy):
    
    def generate_order_spec(self, leg_id, unique_leg_id, leg_config, timestamp, spot_price):
        """Generate order with your logic"""
        # Calculate strike
        strike = self._calculate_strike(leg_config, spot_price)
        
        # Get option data
        option_df = self._get_option_data(strike, leg_config, timestamp)
        
        # Calculate your strategy-specific data
        strategy_data = {
            'strike': strike,
            'ticker': ...,
            'your_threshold': ...,  # Your logic here
            'ready_to_execute': False
        }
        
        return OrderSpec(
            order_id=f"{leg_id}_{int(timestamp.timestamp())}",
            leg_id=leg_id,
            unique_leg_id=unique_leg_id,
            leg_config=leg_config,
            timestamp_created=timestamp,
            strategy_type='MY_NEW_STRATEGY',
            strategy_data=strategy_data
        )
    
    def can_execute(self, order_spec, timestamp, spot_price):
        """Check if your condition is met"""
        # Your logic here
        # Return True if should execute
        return condition_met
    
    def execute(self, order_spec, timestamp, spot_price, TRADE_DICT, order_book):
        """Execute the order"""
        # Use data from order_spec.strategy_data
        # Update TRADE_DICT and order_book
        return TRADE_DICT, order_book
```

### Step 2: Register Strategy

```python
# In entry_manager.py, update _register_strategies()
def _register_strategies(self):
    self.strategy_registry = {
        'IMMEDIATE': ImmediateEntryStrategy(...),
        'MOMENTUM': MomentumEntryStrategy(...),
        'RANGE_BREAKOUT': RangeBreakoutStrategy(...),
        'MY_NEW_STRATEGY': MyNewStrategy(...)  # Add here
    }

# Update _determine_strategy_type()
def _determine_strategy_type(self, leg_config):
    if leg_config.get('my_new_toggle'):
        return 'MY_NEW_STRATEGY'
    # ... rest of logic
```

---

## 🧪 Testing

### Run All Tests

```bash
cd entry_manager_implementation
python test_entry_manager.py
```

### Run Specific Test

```python
python -m unittest test_entry_manager.TestImmediateStrategy
```

### Write Custom Tests

```python
import unittest
from entry_manager import EntryManager

class TestMyScenario(unittest.TestCase):
    def test_my_case(self):
        entry_manager = EntryManager(...)
        # Your test logic
        self.assertEqual(result, expected)
```

---

## 🔄 Migration from Old System

### Old Way

```python
# Old: Everything in one method
TRADE_DICT, order_book, orders, day_breaker = entry_manager.entry(
    index=timestamp,
    order=leg_config,
    spot=spot_price,
    leg_id=leg_id,
    TRADE_DICT=TRADE_DICT,
    order_book=order_book,
    orders=orders
)
```

### New Way

```python
# New: Two phases

# PHASE 1: Submit (once at entry time)
order_id = entry_manager.submit_order(
    leg_id=leg_id,
    leg_config=leg_config,
    timestamp=timestamp,
    spot_price=spot_price
)

# PHASE 2: Execute (every minute)
TRADE_DICT, order_book, executed = entry_manager.execute_pending_entries(
    timestamp=timestamp,
    spot_price=spot_price,
    TRADE_DICT=TRADE_DICT,
    order_book=order_book
)
```

### Migration Checklist

- [ ] Replace `Entry_Execution` imports with `EntryManager`
- [ ] Split entry calls into submit_order() and execute_pending_entries()
- [ ] Move submit_order() to entry time
- [ ] Call execute_pending_entries() every minute
- [ ] Update position creation to handle executed_ids
- [ ] Test with existing leg configurations
- [ ] Verify results match old system

---

## 📚 API Reference

### EntryManager

#### `__init__(options_extractor, spot_df, config, logger=None)`
Initialize the entry manager.

#### `submit_order(leg_id, leg_config, timestamp, spot_price) -> str`
Submit a new order. Returns order_id.

#### `execute_pending_entries(timestamp, spot_price, TRADE_DICT, order_book) -> (dict, dict, list)`
Execute all pending orders that meet conditions. Returns updated TRADE_DICT, order_book, and executed_ids.

#### `get_pending_orders() -> dict`
Get all pending orders.

#### `get_pending_count() -> int`
Get count of pending orders.

#### `get_executed_count() -> int`
Get count of executed orders.

#### `cancel_order(order_id) -> bool`
Cancel a specific order. Returns True if cancelled.

#### `cancel_all_pending()`
Cancel all pending orders.

#### `get_order_status(order_id) -> dict`
Get status of specific order.

#### `get_statistics() -> dict`
Get entry manager statistics.

#### `reset()`
Reset for new day (clears pending and executed).

---

## 📝 Examples

See `usage_examples.py` for comprehensive examples including:
- Basic integration
- Monitoring pending orders
- Cancelling orders
- Testing individual strategies
- Custom scenarios

---

## 🐛 Troubleshooting

### Order not executing
- Check `can_execute()` condition
- Verify option data is available
- Check if order was cancelled
- Use `get_order_status()` to investigate

### Missing data
- Ensure options_extractor is working
- Check timestamp and expiry
- Verify strike calculation

### Wrong strategy selected
- Check `_determine_strategy_type()` logic
- Verify leg_config has correct toggles
- Add debug logging

---

## 📄 License

Internal use only.

---

## 🤝 Contributing

To contribute a new strategy:
1. Create strategy class inheriting EntryStrategy
2. Implement the three required methods
3. Add to strategy registry
4. Write unit tests
5. Update documentation

---

## 📞 Support

For questions or issues, contact the development team.
```