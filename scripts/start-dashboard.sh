#!/bin/sh
exec streamlit run dashboard/app.py --server.address 0.0.0.0 --server.port "${PORT:-10000}" --server.headless true
