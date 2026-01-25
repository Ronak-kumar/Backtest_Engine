from collections import ChainMap
from copy import deepcopy

class OrderSequenceMapper:
    def __init__(self):
        self.main_orders = {}
        self.lazy_legs_orders = {}

        ## Combining both orders into a single dictionary for easy access ##
        ## The ChainMap will update both dictionaries when modified ##
        self.all_order_dict = self.main_orders | self.lazy_legs_orders

    def legid_mapping(self, main_order, lazy_legs_order):

        for index, lazy_leg in lazy_legs_order.items():
            # lazy_legs_order[index]["unique_legid"] = index
            self.lazy_legs_orders[index] = lazy_leg.copy()

        for key, value in main_order.items():
            # main_order[key]["unique_legid"] = key
            self.main_orders[key] = value.copy()

        self.all_order_dict = self.main_orders | self.lazy_legs_orders

        return main_order, lazy_legs_order
    
    def _get_order(self, unique_leg_id):

        order = self.all_order_dict.get(unique_leg_id)
        order['leg_id'] = unique_leg_id

        if order is None:
            return None
        return deepcopy(order)
    
    def get_next_order(self, prev_executed_order, unique_leg_id, hopping_type, leg_to_fetch):
        self.hopping_count_manager(unique_leg_id=unique_leg_id, hopping_type=hopping_type)
        next_ordre_leg_id = prev_executed_order.get(leg_to_fetch, "").replace(".", "_")
        next_order_to_execute = self._get_order(next_ordre_leg_id)

        return deepcopy(next_order_to_execute), next_ordre_leg_id

    def hopping_count_manager(self, unique_leg_id, hopping_type):
        if hopping_type != "":
            ### Changing Hopping Count ###
            self.all_order_dict[unique_leg_id][hopping_type] -= 1