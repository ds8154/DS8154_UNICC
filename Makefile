.PHONY: run backend frontend

backend:
	python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

frontend:
	streamlit run demo.py

run:
	$(MAKE) -j2 backend frontend
