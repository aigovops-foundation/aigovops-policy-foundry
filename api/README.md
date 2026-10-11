# Policy Foundry API

FastAPI service for the AiGovOps Policy Foundry. See the repository root README and DEVIN.md.

```sh
pip install -e ".[dev]"
uvicorn app.main:app --reload        # http://localhost:8000/docs
foundry-demo --out out/bundle --json # run the pipeline, write a signed bundle
foundry-verify out/bundle            # verify it offline
pytest
```
