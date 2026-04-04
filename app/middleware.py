#Multi-Tenant Middleware for Water Billing System.
#Extracts provider context from subdomain, header, or query parameter.

import re
import logging
from typing import Optional, Callable
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("middleware")


class ProviderContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts provider context from incoming requests.
    
    Supports three identification methods (in order of priority):
    1. Subdomain (production): kiambu-water.yourdomain.com
    2. HTTP Header (API clients): X-Provider-Slug
    3. Query Parameter (testing): ?provider=slug
    """
    
    # Routes that don't require provider context
    EXEMPT_ROUTES = {
        "",
        "/",
        "/health",
        "/health/",
        "/api/health",
        "/api/health/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/setup",
        "/setup/",
        "/api/setup",
        "/login",
        "/api/auth/login",
        "/api/auth/register",
    }
    
    def __init__(self, app, allowed_subdomains: list = None):
        super().__init__(app)
        self.allowed_subdomains = allowed_subdomains or []
        logger.info("ProviderContextMiddleware initialized")
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request and extract provider context."""
        
        # Skip if route is exempt
        path = request.url.path.rstrip("/")
        
        if self._is_exempt_route(path):
            return await call_next(request)
        
        try:
            # Try to extract provider slug
            provider_slug = self._extract_provider_slug(request)
            
            if provider_slug:
                # Validate provider exists and is active
                is_valid, provider = self._validate_provider(provider_slug)
                
                if not is_valid:
                    if provider is None:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Provider '{provider_slug}' not found"
                        )
                    else:
                        raise HTTPException(
                            status_code=403,
                            detail=f"Provider '{provider_slug}' is not active"
                        )
                
                # Inject provider into request state
                request.state.provider = provider
                request.state.provider_slug = provider_slug
                
                logger.debug(f"Provider context set: {provider_slug}")
            else:
                # No provider specified - set to None
                request.state.provider = None
                request.state.provider_slug = None
            
            # Process the request
            response = await call_next(request)
            
            return response
            
        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error in provider middleware: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error in provider middleware"}
            )
    
    def _is_exempt_route(self, path: str) -> bool:
        """Check if route is exempt from provider requirement."""
        # Check exact matches
        if path in self.EXEMPT_ROUTES:
            return True
        
        # Check dynamic routes that don't need provider
        exempt_patterns = [
            r"^/static/",
            r"^/templates/",
            r"^/docs",
            r"^/redoc",
            r"^/openapi",
        ]
        
        for pattern in exempt_patterns:
            if re.match(pattern, path):
                return True
        
        return False
    
    def _extract_provider_slug(self, request: Request) -> Optional[str]:
        """Extract provider slug from request using priority methods."""
        
        # Method 1: HTTP Header (highest priority for API clients)
        header_slug = request.headers.get("X-Provider-Slug")
        if header_slug:
            logger.debug(f"Provider from header: {header_slug}")
            return header_slug.strip().lower()
        
        # Method 2: Query Parameter (for testing)
        query_slug = request.query_params.get("provider")
        if query_slug:
            logger.debug(f"Provider from query: {query_slug}")
            return query_slug.strip().lower()
        
        # Method 3: Subdomain (for production)
        subdomain_slug = self._extract_subdomain(request)
        if subdomain_slug:
            logger.debug(f"Provider from subdomain: {subdomain_slug}")
            return subdomain_slug
        
        # No provider specified
        return None
    
    def _extract_subdomain(self, request: Request) -> Optional[str]:
        """Extract provider slug from subdomain."""
        host = request.url.hostname
        
        if not host:
            return None
        
        # Handle localhost (no subdomain)
        if host in ("localhost", "127.0.0.1"):
            return None

        # Ignore common platform-managed preview/service domains.
        # These subdomains identify the hosting app, not a provider tenant.
        ignored_host_suffixes = (
            ".onrender.com",
            ".vercel.app",
            ".railway.app",
            ".up.railway.app",
        )
        if any(host.endswith(suffix) for suffix in ignored_host_suffixes):
            return None
        
        # Split host into parts
        parts = host.split(".")
        
        # If only 2 parts (example.com), no subdomain
        if len(parts) <= 2:
            return None
        
        # Extract subdomain (first part before main domain)
        subdomain = parts[0]
        
        # Validate subdomain format
        if subdomain and subdomain.lower() not in ("www", "api", "admin", "billing"):
            return subdomain.lower()
        
        return None
    
    def _validate_provider(self, slug: str) -> tuple[bool, dict]:
        """Validate provider exists and is active."""
        try:
            from app.mongodb_multitenant import get_provider
            
            provider = get_provider(slug)
            
            if provider is None:
                return False, None
            
            if not provider.get("is_active", True):
                return False, provider
            
            return True, provider
            
        except Exception as e:
            logger.error(f"Error validating provider {slug}: {e}")
            return False, None


class ProviderAuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures authenticated access to provider resources.
    """
    
    # Routes that require admin authentication
    ADMIN_ROUTES_PREFIXES = [
        "/api/admin",
        "/admin",
    ]
    
    # Routes that require customer authentication
    CUSTOMER_ROUTES_PREFIXES = [
        "/api/customer",
        "/customer/portal",
    ]
    
    def __init__(self, app):
        super().__init__(app)
        self.bypass_routes = {
            "/api/admin/login",
            "/api/admin/logout",
            "/api/customer/login",
            "/api/auth/login",
            "/api/auth/register",
        }
        logger.info("ProviderAuthenticationMiddleware initialized")
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        """Ensure proper authentication for protected routes."""
        
        path = request.url.path.rstrip("/")
        
        # Skip exempt routes
        if path in self.bypass_routes:
            return await call_next(request)
        
        # Check if admin route
        is_admin_route = any(path.startswith(prefix) for prefix in self.ADMIN_ROUTES_PREFIXES)
        
        # Check if customer route
        is_customer_route = any(path.startswith(prefix) for prefix in self.CUSTOMER_ROUTES_PREFIXES)
        
        if is_admin_route:
            # Verify admin is authenticated
            if not self._is_admin_authenticated(request):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Admin authentication required"}
                )
        
        if is_customer_route:
            # Verify customer is authenticated
            if not self._is_customer_authenticated(request):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Customer authentication required"}
                )
        
        # Continue to next middleware/handler
        return await call_next(request)
    
    def _is_admin_authenticated(self, request: Request) -> bool:
        """Check if admin is authenticated via session or token."""
        # Check session first
        if request.session.get("is_admin"):
            return True
        
        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Validate token
            token = auth_header[7:]
            if self._validate_admin_token(request, token):
                return True
        
        return False
    
    def _is_customer_authenticated(self, request: Request) -> bool:
        """Check if customer is authenticated via token."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # Basic token validation (would use JWT in production)
            if token and len(token) > 10:
                return True
        return False
    
    def _validate_admin_token(self, request: Request, token: str) -> bool:
        """Validate admin JWT token."""
        try:
            # In production, use proper JWT validation
            # For now, just check token exists and is valid format
            from app.crud_providers import verify_admin_token
            
            provider_slug = getattr(request.state, "provider_slug", None)
            return verify_admin_token(token, provider_slug) if provider_slug else False
            
        except Exception:
            return False


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that provides consistent error handling.
    """
    
    def __init__(self, app):
        super().__init__(app)
        logger.info("ErrorHandlingMiddleware initialized")
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        """Handle errors consistently."""
        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except ValueError as e:
            return JSONResponse(
                status_code=400,
                content={"detail": str(e)}
            )
        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )


# ==================== HELPER FUNCTIONS ====================

def get_provider_context(request: Request) -> dict:
    """Get provider context from request state."""
    return {
        "slug": getattr(request.state, "provider_slug", None),
        "provider": getattr(request.state, "provider", None),
        "database": getattr(request.state, "provider", {}).get("database_name") if getattr(request.state, "provider", None) else None
    }


def require_provider(request: Request) -> dict:
    """Require provider context - raises exception if not present."""
    provider = getattr(request.state, "provider", None)
    if not provider:
        raise HTTPException(
            status_code=400,
            detail="Provider context required"
        )
    return provider


def require_admin(request: Request) -> dict:
    """Require admin authentication - raises exception if not authenticated."""
    if not request.session.get("is_admin"):
        raise HTTPException(
            status_code=401,
            detail="Admin authentication required"
        )
    return request.state.provider


# ==================== EXPORTED FUNCTIONS ====================

__all__ = [
    "ProviderContextMiddleware",
    "ProviderAuthenticationMiddleware",
    "ErrorHandlingMiddleware",
    "get_provider_context",
    "require_provider",
    "require_admin",
]

