from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class TestScenario(Base):
    __tablename__ ="test_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    specification_id = Column(
        Integer,
        ForeignKey("api_specifications.id", ondelete="CASCADE"),
        nullable=False
    )
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # A scenario can contain multiple steps, which are soted by step_order.
    steps = relationship(
        "ScenarioStep",
        back_populates = "scenario",
        cascade = "all, delete-orphan",
        order_by = "ScenarioStep.step_order"
    )


class ScenarioStep(Base):
    __tablename__ = "scenario_steps"

    id = Column(Integer, primary_key = True, index = True)
    scenario_id = Column(
        Integer,
        ForeignKey("test_scenarios.id", ondelete="CASCADE"),
        nullable = False
    )
    endpoint_id = Column(
        Integer,
        ForeignKey("test_scenarios.id", ondelete="CASCADE"),
        nullable = False
    )

    endpoint_id = Column(
        Integer,
        ForeignKey("endpoints.id", ondelete = "CASCADE"),
        nullable = False
    )

    step_order = Column(
        Integer,
        nullable = False,
    ) # Step 1, Step 2, etc.
    payload = Column(JSON, nullable=True) # Request body

    # These two columns are essential for stateful testing
    extract_rules = Column(
        JSON,
        nullable=True,
    ) # Example: [{"json_path": "$.id", "save_as": "user_id"}]
    inject_rules = Column(
        JSON,
        nullable = True,

    ) # Example: [{"target":"path", "field":"uuid", "use_memory": "user_id"}]
    expected_status = Column(Integer, nullable=False)
    scenario = relationship("TestScenario", back_populates = "steps")
    endpoint = relationship("Endpoint")