import os

# DeepEval envoie de la télémétrie (posthog) par défaut : les tests ne doivent rien envoyer.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")
