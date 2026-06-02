"""Compatibility shim for older scikit-learn joblib models.

Some serialized estimators reference a top-level ``_loss`` extension module.
Recent scikit-learn installs expose it as ``sklearn._loss._loss`` instead.
Keeping this tiny module in the repo lets GitHub Actions unpickle those models
without changing the trained artifacts.
"""

from sklearn._loss._loss import *  # noqa: F401,F403
