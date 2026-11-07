# Privacy

Face images can identify people and may be regulated as biometric data.

Before collecting samples:

1. Obtain explicit permission from every person represented in the dataset.
2. Explain the purpose, storage location, retention period, and access.
3. Do not use the application for covert monitoring or unauthorized identity checks.
4. Delete samples and models when consent is withdrawn or the purpose ends.

Face Workbench sends no face images, labels, model weights, or recognition
results to an external service. Runtime files remain under `storage/` and are
excluded from Git. The SQLite database and generated media still need normal
operating-system access controls and backups.
