import cProfile
import pstats
import io
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import os

class ProfilerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        profiler = cProfile.Profile()
        profiler.enable()
        
        response = await call_next(request)
        
        profiler.disable()
        
        # Save plaintext profile
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
        ps.print_stats()
        
        endpoint = request.url.path.replace("/", "_").strip("_")
        profiler_dir = "/profiler_results"
        os.makedirs(profiler_dir, exist_ok=True)
        
        # Save plaintext profile
        with open(os.path.join(profiler_dir, f"profile_{endpoint}.txt"), "w") as f:
            f.write(s.getvalue())
        
        # Save binary profile
        profiler.dump_stats(os.path.join(profiler_dir, f"profile_{endpoint}.prof"))
        
        return response