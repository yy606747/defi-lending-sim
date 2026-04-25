from app.routes.user import user_bp
from app.routes.asset import asset_bp
from app.routes.pledge import pledge_bp
from app.routes.loan import loan_bp
from app.routes.repayment import repayment_bp
from app.routes.liquidation import liquidation_bp
from app.routes.simulation import simulation_bp


def register_routes(app):
    app.register_blueprint(user_bp)
    app.register_blueprint(asset_bp)
    app.register_blueprint(pledge_bp)
    app.register_blueprint(loan_bp)
    app.register_blueprint(repayment_bp)
    app.register_blueprint(liquidation_bp)
    app.register_blueprint(simulation_bp)
