(gnfinder -p 8999 &)
uv run uvicorn wsgi:app --host 0.0.0.0 --port 9714 --use-colors $@