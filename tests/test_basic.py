from opentracing import Format
from opentracing.mocktracer import MockTracer
from opentracing.scope_managers.contextvars import ContextVarsScopeManager

from opentracing_compose import ComposedTracer


def test_init_empty():
    composed_tracer = ComposedTracer([], scope_manager=ContextVarsScopeManager())

    with composed_tracer.start_active_span("foo") as scope:
        scope.span.set_tag("foo", "bar")
        scope.span.log_kv("event", "hi")

        carrier: dict = {}
        composed_tracer.inject(scope.span.context, Format.TEXT_MAP, carrier)
        assert carrier == {}


def test_init_mock():
    mock_tracer = MockTracer()
    composed_tracer = ComposedTracer(
        [mock_tracer], scope_manager=ContextVarsScopeManager()
    )

    with composed_tracer.start_active_span("foo") as scope:
        scope.span.set_tag("foo", "bar")
        scope.span.log_kv("event", "hi")

        carrier: dict = {}
        composed_tracer.inject(scope.span.context, Format.TEXT_MAP, carrier)
        assert carrier == {"ot-tracer-traceid": "2", "ot-tracer-spanid": "1"}

        extracted = composed_tracer.extract(Format.TEXT_MAP, carrier)
        assert len(extracted.composed_contexts) == 1
        mock_context = extracted.composed_contexts[0]
        assert mock_context.span_id == 1
        assert mock_context.trace_id == 2
