#!/usr/bin/env python


from __future__ import annotations

import random
from collections import Counter, defaultdict
from itertools import chain, combinations, repeat

# required for typing
from negmas import *
from numpy.random import choice

# required for development
from scml.std import *
from dataclasses import dataclass

from AS0 import AS0
__all__ = ["AS0"]

class MyAS0(AS0):
    def __init__(self, *args, threshold=None, ptoday=0.70, productivity=0.7, **kwargs):
        super().__init__(*args, **kwargs)
        
    def step(self):
        super().step()

    def first_proposals(self):
        return 

    def counter_all(self, offers, states):
            
        return super().counter_all(offers, states)
