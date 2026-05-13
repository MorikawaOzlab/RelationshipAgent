#!/usr/bin/env python


from __future__ import annotations

from itertools import repeat
import random
from collections import defaultdict

# required for typing
from negmas import *

# required for development
from scml.std import *

from AS0 import AS0
__all__ = ["AS0"]

from dataclasses import dataclass

@dataclass
class TradeStats:
    success_count: int = 0
    fault_count: int = 0

class MyAS0(AS0):
    DO_COUNTER_ALL = True
    DO_FIRST_PROPOSALS = True
    BETTER_DISTRIBUTION = True

    INITIAL_QUANTITY_RATIO = 0.1 # 0step目における提案取引量 maxp * ratio
    QUANTITY_AVG_DECAY = 0.7 # 取引量の加重平均

    partner_weighted_avg_quantity: dict[str, float]
    # 初回提案の内容を一時的に保持するための変数
    partner_first_offer: dict[str, tuple[int, int, int]] 
    quantity_adjust: dict[str, int]

    def __init__(self, *args, threshold=None, ptoday=0.70, productivity=0.7, **kwargs):
        super().__init__(*args, **kwargs)

        # experimental
        if self.BETTER_DISTRIBUTION:
            self.history_table: dict[tuple[str, int, int, int], TradeStats] = defaultdict(TradeStats)
    
        # 加重平均の計算を、negotiationsuccess, negotiation failture, counter allで行う
        # ついでに交渉テーブルも作りたい
        self.partner_weighted_avg_quantity = defaultdict(float)
        self.partner_first_offer = {}
        self.quantity_adjust = defaultdict(int)
        
    def on_negotiation_success(self, contract, mechanism):
        if not self.BETTER_DISTRIBUTION:
            return 
        
        ##==============
        ## 改良した配分
        ##==============
        
        # 交渉結果テーブル作成

        partner = next(p for p in contract.partners if p != self.id)

        agreement = contract.agreement

        quantity = agreement["quantity"]
        delivery_time = agreement["time"]
        unit_price = agreement["unit_price"]

        self.history_table[
            partner,
            quantity,
            delivery_time - self.awi.current_step,
            unit_price,
        ].success_count += 1

        # 加重平均の計算
        self._update_partner_avg_quantity(partner, quantity)
        
        print("avg quantitiy", partner, self.partner_weighted_avg_quantity[partner])

        # print(f"success \n{contract}\n")

    def on_negotiation_failure(self, partners, annotation, mechanism, state):
        # print(f"fialture {partners}: {state}")
        pass
        
    def step(self):
        super().step()

    def first_proposals(self):
        if self.awi.current_step == 0:
            self.init_partner_avg_quantity(self.negotiators.keys())

        offer = self.partner_first_offer = super().first_proposals()

        # print("first proposals\n", offer)
        return offer

    def counter_all(self, offers, states):
        # print("counter offer\n", offers)

        if not self.DO_COUNTER_ALL:
            return super().counter_all(offers, states)
        #　初回提案が終わったので変数をリセット

        response = {}
        
        for partner, offer in offers.items():
            if partner in self.awi.my_consumers:
                response[partner] = SAOResponse(
                    ResponseType.ACCEPT_OFFER, None
                )
            else:
                response[partner] = SAOResponse(
                    ResponseType.END_NEGOTIATION, None
                )

        self.partner_first_offer = response
        return response
    
    def init_partner_avg_quantity(self, partners) -> None:
        """
        交渉パートナーの取引量の初期値をセット
        """
        for partner in partners:
            nmi = self.get_ami(partner)
            if nmi is None: continue
            
            quantity_issue = nmi.issues[QUANTITY]

            self.partner_weighted_avg_quantity[partner] = (
                quantity_issue.max_value + quantity_issue.min_value
            ) * self.INITIAL_QUANTITY_RATIO 

    def distribute_todays_needs(self, partners=None):
        if partners is None:
            partners = self.negotiators.keys()

        if not self.DO_FIRST_PROPOSALS:
            return dict(zip(partners, repeat(0)))

        if not self.BETTER_DISTRIBUTION:
            return super().distribute_todays_needs()
        
        response = dict(zip(partners, repeat(1)))

        # for partner in partners:
        #     if partner in self.awi.my_suppliers:
        #         response[partner] = 5

        # print(self.awi.current_inventory_input)
        return response
    
    def get_current_needs(self):
        awi = self.awi
        day_production = awi.n_lines * self._productivity
        # 仕入れたい数(inventory input高すぎて基本負数)
        supplie_needs = int(
            day_production
            - awi.current_inventory_input
            - awi.total_supplies_at(awi.current_step)
        )
        # 売りたい数(何か間違いがありそう)
        consume_needs = int(
            max(
                0,
                min(self.awi.n_lines, day_production + awi.current_inventory_input)
                - awi.total_sales_at(awi.current_step),
            )
        )

        return supplie_needs, consume_needs
    
    def smart_price(self, partner, is_first_proposal=False, is_counter_offer=False):
        """改善された価格戦略"""
        nmi = self.get_nmi(partner)
        if nmi is None:
            return 15
        issues = nmi.issues
        pissue = issues[UNIT_PRICE]
        minp, maxp = pissue.min_value, pissue.max_value

        # パートナーの成功率を考慮
        success_rate = self.partner_success_rate[partner]

        if self.is_consumer(partner):
            return minp
        else:
            return maxp
        
    def _update_partner_avg_quantity(self, partner, quantity):
        """
        加重平均の計算
        """
        current_quantity = self.partner_weighted_avg_quantity[partner]
        next_quantity = quantity

        self.partner_weighted_avg_quantity[partner] = (
            (1-self.QUANTITY_AVG_DECAY) * current_quantity + self.QUANTITY_AVG_DECAY * next_quantity
        )