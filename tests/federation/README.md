# Federation Stress Harness

Run fast CI gate via pytest:

```bash
pytest tests/federation/test_stress_harness.py
```

Run full battery manually:

```bash
python -m tests.federation.stress_battery
```

Run profile-based CLI:

```bash
python cmd/qso-node/stress_cli.py --profile 100k
python cmd/qso-node/stress_cli.py --profile 1m
python cmd/qso-node/stress_cli.py --profile cascade
python cmd/qso-node/stress_cli.py --profile policy-conflict
```
