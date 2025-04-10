import numpy as np
import plotly.graph_objects as go

# Create the grid
last_interaction = np.linspace(0, 10, 100)
importance = np.linspace(0, 10, 100)
L, I = np.meshgrid(last_interaction, importance)

# Calculate Z
Z = 1 / (1 + np.exp( -0.01 * ( L**2 + I**2 + (np.maximum(0, I - 8.5))**4 ) ))

# Create hover text for each cell
hover_text = np.round(Z, 2).astype(str)
hover_text = np.char.add("Score: ", hover_text)

# Create interactive heatmap
fig = go.Figure(data=go.Heatmap(
    z=Z,
    y=importance,    # Y-axis: Importance
    x=last_interaction,  # X-axis: Last Interaction
    text=hover_text,    # Custom hover text
    colorscale='RdBu',
    reversescale=True,
    colorbar=dict(title='Score')
))

# Add a contour line for the threshold
threshold = 0.7
fig.add_trace(go.Contour(
    z=Z,
    x=last_interaction,
    y=importance,
    contours=dict(
        start=threshold,
        end=threshold,
        size=0.01,
        coloring='lines'
    ),
    line=dict(color='black', width=2),
    showscale=False
))

fig.update_layout(
    title='Heatmap: 1 / (1 + np.exp( -0.01 * ( L**2 + I**2 + (np.maximum(0, I - 8.5))**4 ) ))',
    xaxis_title='Importance',
    yaxis_title='Last Interaction',
    height=600,
    width=800
)

fig.show()
