"""Le endpoint de sante repond, sans dependre de la base ni d'un fournisseur LLM."""

from httpx import ASGITransport, AsyncClient

from app.main import create_app


async def test_health_reports_ok() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reponse = await client.get("/health")

    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}
