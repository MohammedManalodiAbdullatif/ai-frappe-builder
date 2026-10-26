import pytest
from httpx import AsyncClient, ASGITransport
from ai_frappe_builder.main import app
from ai_frappe_builder.database import init_db, create_session, get_db
from ai_frappe_builder.agents.orchestrator import get_or_create_orchestrator_session


@pytest.mark.asyncio
async def test_update_plan_api():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a session in DB
        async for db in get_db():
            sess = await create_session(db, client_name="test_client")
            session_id = sess.id
            break

        orch_sess = get_or_create_orchestrator_session(session_id)

        # Update plan via PUT
        payload = {
            "app": {
                "app_name": "car_rental",
                "title": "Car Rental",
                "modules": ["Fleet"],
                "roles": ["Fleet Manager", "System Manager"],
                "doctypes": [
                    {
                        "name": "Vehicle",
                        "module": "Fleet",
                        "fields": [
                            {"fieldname": "make", "label": "Make", "fieldtype": "Data"}
                        ],
                        "permissions": [
                            {"role": "System Manager", "read": True, "write": True, "create": True, "delete": True},
                            {"role": "Fleet Manager", "read": True, "write": True}
                        ]
                    },
                    {
                        "name": "Rental Booking",
                        "module": "Fleet",
                        "fields": [
                            {"fieldname": "customer", "label": "Customer", "fieldtype": "Data"},
                            {"fieldname": "vehicle", "label": "Vehicle", "fieldtype": "Link", "options": "Vehicle"}
                        ],
                        "permissions": [
                            {"role": "System Manager", "read": True, "write": True, "create": True, "delete": True},
                            {"role": "Fleet Manager", "read": True, "write": True}
                        ]
                    }
                ],
                "workflows": []
            }
        }

        res = await client.put(f"/api/v1/plan/{session_id}", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "ok"
        assert len(data["app"]["doctypes"]) == 2
        assert data["validation"]["is_valid"] is True, f"Validation errors: {data['validation']['errors']}"
        assert orch_sess.spec is not None
        assert orch_sess.spec.app.app_name == "car_rental"
