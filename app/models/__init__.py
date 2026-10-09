"""Import all models so SQLAlchemy metadata is populated."""
from app.models.user import User, LoginHistory
from app.models.customer import Customer, KYCDocument
from app.models.loan import Loan, LoanStatusHistory
from app.models.collateral import CollateralItem
from app.models.metal_rate import MetalRateHistory
from app.models.repayment import Repayment, InterestAccrual
from app.models.audit import AuditLog
from app.models.app_settings import AppSetting, BackupHistory


def _register_all():
    """Called by connection.py to ensure all models are imported."""
    pass
