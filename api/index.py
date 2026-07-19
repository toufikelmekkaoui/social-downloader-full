import sys
import os

# هكا غانخلّيو Vercel يقرأ ديريكت من مجلد backend القديم بلا ما نقيسوه
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

# استدعاء الـ app من المجلد القديم ديالك
from app import create_app

app = create_app()