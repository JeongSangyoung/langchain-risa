import os

import reflex as rx
os.path.dirname(os.path.abspath(__file__))

from .exp import index 
from .llm import llm
from .naimy import naimy
from .risa import risa


app = rx.App()
app.add_page(index)
app.add_page(llm)
app.add_page(naimy)
app.add_page(risa)
