# Require explicit decision-tree fallbacks

The visual Decision tree editor generates ordered Polars `when`/`then` chains with a required `otherwise` branch. Authors must state `None` explicitly when null is intended, preventing implicit null outcomes and making every row's fallback behavior auditable.
