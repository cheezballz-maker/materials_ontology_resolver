"""Bound Stage B native chemistry in a reusable Windows-compatible child."""

from collections import Counter
from math import isfinite
from multiprocessing import get_context
from time import perf_counter


class _ParserRelay:
    def __init__(self, link):
        self.link = link
        self.failures = 0

    def _request(self, method, name):
        self.link.send(("parser", method, name))
        result = self.link.recv()
        self.failures += result["status"]=="ERROR"
        return result

    def opsin(self, name):
        return self._request("opsin",name)

    def opsin_cml(self, name):
        return self._request("opsin_cml",name)


def _serve(link):
    from rdkit import rdBase
    from canonical_registry.nomenclature_interpretation import InterpretationFramework
    from canonical_registry.nomenclature_interpretation.cosing_preview_adapter import COSMETICS_FUNCTIONS
    from .benchmark_readiness import peak_rss
    from .stage_b_v3 import _build

    timings = Counter()
    bridge = _ParserRelay(link)
    framework = InterpretationFramework(name_parser=bridge,
        function_vocabularies={"cosmetics":COSMETICS_FUNCTIONS},timings=timings)
    with link, rdBase.BlockLogs():
        link.send(("ready",))
        while True:
            try:
                packet = link.recv()
            except EOFError:
                return
            if packet is None:
                return
            row,item,parent,aliases,provenance,version = packet
            timings.clear()
            try:
                prediction = _build(framework,bridge,row,item,lambda *_:(parent,aliases,provenance),version,timings)
            except Exception as exc:
                link.send(("exception",type(exc).__name__,str(exc)[:300]))
                return
            link.send(("complete",prediction,dict(timings),peak_rss()))


class StageBWorker:
    """The child holds no registry or provider connection. A deadline kills native work."""

    def __init__(self, bridge, *, startup_seconds=20, target=_serve):
        self.bridge = bridge
        self.startup_seconds = startup_seconds
        self.target = target
        self.process = self.link = None
        self.lifecycle = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self, *, terminate=False):
        if self.process is None:
            return
        started = perf_counter()
        process, link = self.process,self.link
        self.process = self.link = None
        if process.is_alive() and not terminate:
            try:
                link.send(None)
            except OSError:
                pass
            process.join(0.3)
        if process.is_alive():
            process.terminate()
            process.join(1)
        if process.is_alive():
            process.kill()
            process.join(2)
        if process.is_alive():
            raise RuntimeError("Failed to reap the Stage B worker")
        self.lifecycle.append({"event":"stopped","pid":process.pid,"exit_code":process.exitcode,
                               "elapsed_seconds":perf_counter()-started})
        link.close()
        process.close()

    def _start(self):
        started = perf_counter()
        context = get_context("spawn")
        parent,child = context.Pipe()
        process = context.Process(target=self.target,args=(child,),daemon=True)
        try:
            process.start()
        except BaseException:
            parent.close()
            process.close()
            raise
        finally:
            child.close()
        self.process,self.link = process,parent
        try:
            if not parent.poll(self.startup_seconds) or parent.recv()!=("ready",):
                raise TimeoutError("Stage B worker did not initialize")
        except BaseException:
            self.close(terminate=True)
            raise
        self.lifecycle.append({"event":"started","pid":process.pid,"elapsed_seconds":perf_counter()-started})

    def run(self, packet, seconds):
        if not isfinite(seconds) or seconds<=0:
            raise ValueError("The record budget must be positive and finite")
        if self.process is None:
            started = perf_counter()
            try:
                self._start()
            except (EOFError,OSError) as exc:
                return {"prediction":None,"budget_seconds":seconds,"provider_activity":[],
                        "reason":"WORKER_STARTUP_FAILURE","error":type(exc).__name__,
                        "elapsed_seconds":perf_counter()-started}
        started = perf_counter()
        deadline = started+seconds
        result = {"prediction":None,"budget_seconds":seconds,"provider_activity":[],"pid":self.process.pid}
        try:
            self.link.send(packet)
            while self.link.poll(max(0,deadline-perf_counter())):
                message = self.link.recv()
                if perf_counter()>deadline:
                    break
                match message:
                    case "complete", prediction, timings, rss:
                        result.update(prediction=prediction, timings=timings, worker_peak_bytes=rss,
                                      reason=None if prediction is not None else "RETRYABLE_PROVIDER_FAILURE")
                        break
                    case "exception", error, detail:
                        result.update(reason="WORKER_EXCEPTION",detail=detail,error=error)
                        self.close(terminate=True)
                        break
                    case "parser", method, query if method in ("opsin","opsin_cml"):
                        original = self.bridge.timeout
                        self.bridge.timeout = min(original,max(0.001,deadline-perf_counter()))
                        try:
                            reply = getattr(self.bridge,method)(query)
                        except Exception as exc:
                            reply = {"status":"ERROR","diagnostic":type(exc).__name__}
                        finally:
                            self.bridge.timeout = original
                        result["provider_activity"].append({"method":method,"query":query,"status":reply["status"],
                                                           "diagnostic":reply.get("diagnostic")})
                        if perf_counter()>deadline:
                            if reply["status"]=="ERROR":
                                result["reason"] = "RETRYABLE_PROVIDER_FAILURE"
                                self.close(terminate=True)
                            break
                        self.link.send(reply)
                    case _:
                        result["reason"] = "INVALID_WORKER_RESPONSE"
                        self.close(terminate=True)
                        break
            if "reason" not in result:
                result["reason"] = "RECONCILIATION_TIMEOUT"
                self.close(terminate=True)
        except (EOFError, OSError) as exc:
            self.close(terminate=True)
            result.update(reason="WORKER_EXIT",error=type(exc).__name__)
        except BaseException:
            self.close(terminate=True)
            raise
        result["elapsed_seconds"] = perf_counter()-started
        return result
