import os
import pytest

os.environ["BOT_TOKEN"] = ""
os.environ["AQI_TOKEN"] = ""

pytest.main()
