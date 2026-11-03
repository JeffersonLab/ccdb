"""The request-scoped provider of the HTTP API: one session per request on the application's engine"""
from fastapi import Request


def provider_dependency(request: Request):
    """An AlchemyProvider for this request; its session closes when the request ends"""
    provider = request.app.state.database.provider()
    try:
        yield provider
    finally:
        provider.session.close()
