from agents.base import BaseAdvisor, get_openai_client
from agents.board_chair import BoardChair
from agents.financial import FinancialAdvisor
from agents.operations import OperationsAdvisor
from agents.marketing import MarketingAdvisor
from agents.legal import LegalAdvisor
from agents.risk import RiskAdvisor
from agents.commodity_risk import CommodityRiskAdvisor
from agents.livestock import LivestockAdvisor
from agents.sustainability import SustainabilityAdvisor
from agents.agronomist import AgronomistAdvisor

ADVISOR_CLASSES = {
    "financial": FinancialAdvisor,
    "operations": OperationsAdvisor,
    "marketing": MarketingAdvisor,
    "legal": LegalAdvisor,
    "risk": RiskAdvisor,
    "commodity_risk": CommodityRiskAdvisor,
    "livestock": LivestockAdvisor,
    "sustainability": SustainabilityAdvisor,
    "agronomist": AgronomistAdvisor,
}

BASE_ADVISOR_IDS = ["financial", "operations", "marketing", "legal", "risk"]
OPTIONAL_ADVISOR_IDS = ["commodity_risk", "livestock", "sustainability", "agronomist"]

BASE_ADVISORS = {aid: ADVISOR_CLASSES[aid].info() for aid in BASE_ADVISOR_IDS}
OPTIONAL_ADVISORS = {aid: ADVISOR_CLASSES[aid].info() for aid in OPTIONAL_ADVISOR_IDS}
ALL_ADVISORS = {**BASE_ADVISORS, **OPTIONAL_ADVISORS}
