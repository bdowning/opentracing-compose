from typing import Iterable, List

from opentracing.scope_manager import ScopeManager
from opentracing.span import Span, SpanContext
from opentracing.tracer import Tracer


class ComposedSpanContext(SpanContext):
    _composed_contexts: List[SpanContext]

    def __init__(self, composed_contexts: Iterable[SpanContext]):
        super().__init__()
        self._composed_contexts = list(composed_contexts)

    @property
    def baggage(self):
        raise Exception("Unimplemented")

    @property
    def composed_contexts(self):
        return self._composed_contexts


class ComposedSpan(Span):
    _composed_spans: List[Span]

    def __init__(self, tracer, composed_spans: Iterable[Span]):
        self._composed_spans = list(composed_spans)
        contexts = [s.context for s in self._composed_spans]
        super().__init__(tracer, ComposedSpanContext(contexts))

    @property
    def composed_contexts(self):
        return self._context._composed_contexts

    def set_operation_name(self, operation_name):
        for span in self._composed_spans:
            span.set_operation_name(operation_name)
        return self

    def finish(self, finish_time=None):
        for span in self._composed_spans:
            span.finish(finish_time)

    def set_tag(self, key, value):
        for span in self._composed_spans:
            span.set_tag(key, value)
        return self

    def log_kv(self, key_values, timestamp=None):
        for span in self._composed_spans:
            span.log_kv(key_values, timestamp)
        return self

    def set_baggage_item(self, key, value):
        for span in self._composed_spans:
            span.set_baggage_item(key, value)
        return self

    def get_baggage_item(self, key):
        raise Exception("Unimplemented")


class ComposedTracer(Tracer):
    _composed_tracers: List[Tracer]

    def __init__(self, composed_tracers: Iterable[Tracer], scope_manager=None):
        self._scope_manager = ScopeManager() if scope_manager is None else scope_manager
        self._composed_tracers = list(composed_tracers)
        self._none_composed_contexts = [None for x in self._composed_tracers]

    def start_active_span(
        self,
        operation_name,
        child_of=None,
        references=None,
        tags=None,
        start_time=None,
        ignore_active_span=False,
        finish_on_close=True,
    ):
        span = self.start_span(
            operation_name=operation_name,
            child_of=child_of,
            references=references,
            tags=tags,
            start_time=start_time,
            ignore_active_span=ignore_active_span,
        )

        return self.scope_manager.activate(span, finish_on_close)

    def start_span(
        self,
        operation_name=None,
        child_of=None,
        references=None,
        tags=None,
        start_time=None,
        ignore_active_span=False,
    ) -> ComposedSpan:
        parent = child_of

        if not ignore_active_span and not parent and self.active_span is not None:
            parent = self.active_span

        if parent:
            parent_contexts = parent.composed_contexts
        else:
            parent_contexts = self._none_composed_contexts

        if references:
            raise Exception("Unimplemented")

        spans = [
            tracer.start_span(
                operation_name=operation_name,
                child_of=parent,
                references=references,
                tags=tags,
                start_time=start_time,
                ignore_active_span=True,
            )
            for tracer, parent in zip(self._composed_tracers, parent_contexts)
        ]
        return ComposedSpan(self, spans)

    def inject(self, span_context, format, carrier):
        for tracer, context in zip(
            self._composed_tracers, span_context._composed_contexts
        ):
            tracer.inject(context, format, carrier)

    def extract(self, format, carrier):
        contexts = [t.extract(format, carrier) for t in self._composed_tracers]
        return ComposedSpanContext(contexts)
