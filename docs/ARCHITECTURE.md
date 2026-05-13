# Architecture Diagram

## High-Level Architecture

```mermaid
graph TD
    A[User Interface - Flet] --> B[API Wrapper / VexAgent Class]
    B --> C[Core Vex Agent]
    C --> D[LLM Providers: Gemini/Claude/OpenAI]
    C --> E[Tools: FFmpeg, Whisper, MoviePy, etc.]
    C --> F[State Management & Timeline]
    A --> G[Video Preview: flet-video]
    A --> H[Project Files & Exports]
    
    subgraph Desktop App
        A
        G
    end
    
    subgraph Vex Backend
        B
        C
        D
        E
        F
    end
```

## Detailed Component Breakdown

- **Frontend (Flet)**: Chat interface, video player, timeline view
- **Backend Wrapper**: `VexAgent` class that exposes high-level methods
- **Original Vex**: Forked and integrated as a submodule or copied core modules

For a visual diagram, see the Mermaid code above (renders nicely in GitHub).