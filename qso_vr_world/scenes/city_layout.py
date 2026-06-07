def generate_city_grid(num_rows=5, num_cols=5, spacing=5.0):
    return {f"node_{r}_{c}": (r * spacing, 0.0, c * spacing) for r in range(num_rows) for c in range(num_cols)}
