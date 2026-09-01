from collections.abc import AsyncIterator

from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.modules.activity.service import (
    VisitorQueryService,
    VisitorTrackingService,
)
from app.api.modules.admin.service import DashboardService
from app.api.modules.advisors.service import ElectricalAdvisorService
from app.api.modules.auth.service import (
    JwtService,
    LoginService,
    LogoutSessionService,
    RefreshSessionService,
)
from app.api.modules.catalog.service import (
    CatalogAdministrationService,
    CatalogQueryService,
    ProductManagementService,
    ReviewSubmissionService,
    StockSubscriptionService,
)
from app.api.modules.checkout.service import PricingService
from app.api.modules.custom_boards.service import (
    BoardEstimationService,
    BoardStatusTransitionService,
    CustomBoardCreationService,
    CustomBoardManagementService,
    CustomBoardPublicQueryService,
)
from app.api.modules.customers.service import (
    CompanyManagementService,
    CustomerAuthenticationService,
    CustomerProfileService,
)
from app.api.modules.delivery.service import DeliveryLocationService
from app.api.modules.leads.service import (
    LeadCreationService,
    LeadManagementService,
    LeadStatusTransitionService,
)
from app.api.modules.orders.service import (
    CustomerOrderHistoryService,
    OrderCreationService,
    OrderManagementService,
    OrderStatusTransitionService,
)
from app.api.modules.outbox.service import OutboxRecoveryService
from app.clients.nova_poshta import NovaPoshtaClient
from app.database.engine import SessionFactory
from app.database.uow import UnitOfWork
from app.services.rate_limit import RateLimitService
from app.settings import Config, get_config


class AppProvider(Provider):
    """Application provider for dependency injection."""

    @provide(scope=Scope.APP)
    def get_config(self) -> Config:
        return get_config()

    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        async with SessionFactory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    async def get_uow(self, session: AsyncSession) -> AsyncIterator[UnitOfWork]:
        async with UnitOfWork(session) as uow:
            yield uow

    @provide(scope=Scope.APP)
    async def get_redis(self, config: Config) -> AsyncIterator[Redis]:
        redis = Redis.from_url(config.redis_url, decode_responses=True)
        try:
            yield redis
        finally:
            await redis.aclose()

    @provide(scope=Scope.APP)
    async def get_nova_poshta_client(
        self,
        config: Config,
    ) -> AsyncIterator[NovaPoshtaClient]:
        client = NovaPoshtaClient(config.nova_poshta)
        try:
            yield client
        finally:
            await client.close()


class ServicesProvider(Provider):
    """Services provider for dependency injection."""

    @provide(scope=Scope.APP)
    def get_jwt_service(self, config: Config) -> JwtService:
        return JwtService(config)

    @provide(scope=Scope.APP)
    def get_rate_limit_service(
        self,
        redis: Redis,
        config: Config,
    ) -> RateLimitService:
        return RateLimitService(redis, config)

    @provide(scope=Scope.REQUEST)
    def get_delivery_location_service(
        self,
        client: NovaPoshtaClient,
    ) -> DeliveryLocationService:
        return DeliveryLocationService(client)

    @provide(scope=Scope.REQUEST)
    def get_visitor_tracking_service(self, uow: UnitOfWork) -> VisitorTrackingService:
        return VisitorTrackingService(uow)

    @provide(scope=Scope.REQUEST)
    def get_visitor_query_service(self, uow: UnitOfWork) -> VisitorQueryService:
        return VisitorQueryService(uow)

    @provide(scope=Scope.REQUEST)
    def get_electrical_advisor_service(
        self,
        uow: UnitOfWork,
    ) -> ElectricalAdvisorService:
        return ElectricalAdvisorService(uow)

    @provide(scope=Scope.REQUEST)
    def get_board_estimation_service(self) -> BoardEstimationService:
        return BoardEstimationService()

    @provide(scope=Scope.REQUEST)
    def get_customer_authentication_service(
        self,
        uow: UnitOfWork,
        jwt_service: JwtService,
    ) -> CustomerAuthenticationService:
        return CustomerAuthenticationService(uow, jwt_service)

    @provide(scope=Scope.REQUEST)
    def get_customer_profile_service(self, uow: UnitOfWork) -> CustomerProfileService:
        return CustomerProfileService(uow)

    @provide(scope=Scope.REQUEST)
    def get_company_management_service(
        self, uow: UnitOfWork
    ) -> CompanyManagementService:
        return CompanyManagementService(uow)

    @provide(scope=Scope.REQUEST)
    def get_custom_board_creation_service(
        self,
        uow: UnitOfWork,
        estimator: BoardEstimationService,
    ) -> CustomBoardCreationService:
        return CustomBoardCreationService(uow, estimator)

    @provide(scope=Scope.REQUEST)
    def get_board_status_transition_service(self) -> BoardStatusTransitionService:
        return BoardStatusTransitionService()

    @provide(scope=Scope.REQUEST)
    def get_custom_board_management_service(
        self,
        uow: UnitOfWork,
        transitions: BoardStatusTransitionService,
    ) -> CustomBoardManagementService:
        return CustomBoardManagementService(uow, transitions)

    @provide(scope=Scope.REQUEST)
    def get_custom_board_public_query_service(
        self,
        uow: UnitOfWork,
    ) -> CustomBoardPublicQueryService:
        return CustomBoardPublicQueryService(uow)

    @provide(scope=Scope.REQUEST)
    def get_login_service(
        self, uow: UnitOfWork, jwt_service: JwtService
    ) -> LoginService:
        return LoginService(uow, jwt_service)

    @provide(scope=Scope.REQUEST)
    def get_refresh_session_service(
        self,
        uow: UnitOfWork,
        jwt_service: JwtService,
    ) -> RefreshSessionService:
        return RefreshSessionService(uow, jwt_service)

    @provide(scope=Scope.REQUEST)
    def get_logout_session_service(
        self,
        uow: UnitOfWork,
        jwt_service: JwtService,
    ) -> LogoutSessionService:
        return LogoutSessionService(uow, jwt_service)

    @provide(scope=Scope.REQUEST)
    def get_catalog_query_service(self, uow: UnitOfWork) -> CatalogQueryService:
        return CatalogQueryService(uow)

    @provide(scope=Scope.REQUEST)
    def get_catalog_administration_service(
        self,
        uow: UnitOfWork,
    ) -> CatalogAdministrationService:
        return CatalogAdministrationService(uow)

    @provide(scope=Scope.REQUEST)
    def get_product_management_service(
        self,
        uow: UnitOfWork,
    ) -> ProductManagementService:
        return ProductManagementService(uow)

    @provide(scope=Scope.REQUEST)
    def get_review_submission_service(
        self,
        uow: UnitOfWork,
    ) -> ReviewSubmissionService:
        return ReviewSubmissionService(uow)

    @provide(scope=Scope.REQUEST)
    def get_stock_subscription_service(
        self,
        uow: UnitOfWork,
    ) -> StockSubscriptionService:
        return StockSubscriptionService(uow)

    @provide(scope=Scope.REQUEST)
    def get_pricing_service(self, uow: UnitOfWork) -> PricingService:
        return PricingService(uow)

    @provide(scope=Scope.REQUEST)
    def get_order_creation_service(
        self,
        uow: UnitOfWork,
        pricing_service: PricingService,
    ) -> OrderCreationService:
        return OrderCreationService(uow, pricing_service)

    @provide(scope=Scope.REQUEST)
    def get_order_status_transition_service(self) -> OrderStatusTransitionService:
        return OrderStatusTransitionService()

    @provide(scope=Scope.REQUEST)
    def get_customer_order_history_service(
        self,
        uow: UnitOfWork,
    ) -> CustomerOrderHistoryService:
        return CustomerOrderHistoryService(uow)

    @provide(scope=Scope.REQUEST)
    def get_order_management_service(
        self,
        uow: UnitOfWork,
        transitions: OrderStatusTransitionService,
    ) -> OrderManagementService:
        return OrderManagementService(uow, transitions)

    @provide(scope=Scope.REQUEST)
    def get_lead_creation_service(self, uow: UnitOfWork) -> LeadCreationService:
        return LeadCreationService(uow)

    @provide(scope=Scope.REQUEST)
    def get_lead_status_transition_service(self) -> LeadStatusTransitionService:
        return LeadStatusTransitionService()

    @provide(scope=Scope.REQUEST)
    def get_lead_management_service(
        self,
        uow: UnitOfWork,
        transitions: LeadStatusTransitionService,
    ) -> LeadManagementService:
        return LeadManagementService(uow, transitions)

    @provide(scope=Scope.REQUEST)
    def get_dashboard_service(
        self,
        uow: UnitOfWork,
        config: Config,
    ) -> DashboardService:
        return DashboardService(uow, config)

    @provide(scope=Scope.REQUEST)
    def get_outbox_recovery_service(self, uow: UnitOfWork) -> OutboxRecoveryService:
        return OutboxRecoveryService(uow)


def get_async_container() -> AsyncContainer:
    return make_async_container(
        AppProvider(),
        ServicesProvider(),
    )
