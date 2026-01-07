# NEURALFLOW: AI Rhythm

**NEURALFLOW** is a rhythm game that uses the power of AI to generate unique levels on the fly. Simply provide a theme or an atmospheric vibe, and the game's AI, powered by Ollama, will create a custom level complete with its own color palette, speed, and cinematic introduction.

## Features

- **AI-Generated Levels:** Every level is uniquely crafted by an AI based on your input.
- **Multiple Game Modes:** Choose between 2-lane, 4-lane, and a circular OSU mode.
- **Customizable Experience:** Tweak the scroll speed and select different AI models in the settings.
- **Dynamic Visuals:** The game features a clean, retro-futuristic aesthetic with dynamic backgrounds and particle effects.
- **Custom Musics (Beta)** Adding your favourit beats to the game, paired with matching levels

## Requirements

- **Python 3:** The game is written in Python 3.
- **Pygame:** A cross-platform set of Python modules designed for writing video games.
- **Requests:** A simple, yet elegant HTTP library.
- **Ollama:** An open-source tool for running large language models locally.
- **Mistral or Gemma3** Though other LMs would work, those two models are tested and passed without errors.

## Ollama Installation

This project requires Ollama to be installed and running on your machine.

### macOS

1.  Download the Ollama application from the [official website](https://ollama.com/download/mac).
2.  Open the downloaded `.dmg` file and drag the `Ollama.app` into your Applications folder.

### Linux

Run the following command in your terminal:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

You can view the script source [here](https://github.com/ollama/ollama/blob/main/scripts/install.sh).

### Windows

1.  Download the Ollama installer from the [official website](https://ollama.com/download/windows).
2.  Run the downloaded executable and follow the installation prompts.

### Pulling a Model (Crucial Step!)

After installing Ollama, you need to pull a model for the game to use. The game is pre-configured to use `mistral:7b` and `gemma3:270m`(Recommended for faster inference), but you can use any model. Open your terminal or command prompt and run:

```bash
ollama pull mistral:7b
```
```bash
ollama pull gemma3:270m
```

## How to Play

1.  **Run the game:**
    ```bash
    pip install -r requirements.txt
    python main.py
    ```
2.  **Navigate the menus:** Use the **UP** and **DOWN** arrow keys to navigate and **ENTER** to select.
3.  **Enter a theme:** In the "NEW FLOW" menu, type any theme or vibe you can think of (e.g., "cyberpunk city," "oceanic tranquility," "cosmic horror", you can also specify the BPM of your preferred song).
4.  **Play the game:**
    -   **2K Mode:** Use the **LEFT** and **RIGHT** arrow keys (or **A** and **D**) to hit the notes.
    -   **4K Mode:** Use the **D, F, J, K** keys to hit the notes.
    -   **OSU Mode:** Use your mouse to move the cursor and the **Z** or **X** keys (or mouse clicks) to hit the circles.

## Configuration

You can access the settings menu from the main menu.

-   **AI Model:** Press **1** to cycle through the available Ollama models on your system.
-   **Game Mode:** Press **M** to switch between 2K, 4K, and OSU modes.
-   **Scroll Speed:** Press **S** to change the note scroll speed (not applicable to OSU mode).

## Troubleshooting

-   **"Ollama generation failed" error:**
    -   Make sure Ollama is running on your computer.
    -   Ensure you have pulled a model (e.g., `ollama pull mistral`).
    -   Check your firewall settings to ensure the game is not blocked from accessing `http://localhost:11434`.
-   **Game runs slowly:**
    -   Ensure your computer meets the minimum requirements for running Pygame.
    -   Close other applications to free up system resources.
