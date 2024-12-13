# Distributed Mutual Exclusion Implementation

This project implements a distributed mutual exclusion system using three different algorithms:
1. Token-based mutual exclusion between heavyweight processes
2. Lamport's algorithm for ProcessA's lightweight processes
3. Ricart-Agrawala's algorithm for ProcessB's lightweight processes

## System Architecture

The system consists of:
- 2 heavyweight processes (ProcessA and ProcessB)
- 6 lightweight processes (3 for each heavyweight process)
- Asynchronous socket-based communication
- Logical clocks for maintaining distributed ordering

## Requirements

- Python 3.7 or higher
- No external dependencies required

## Project Structure

```
src/
├── common/
│   ├── message.py      # Message definitions and types
│   └── constants.py    # System configuration
├── processes/
│   ├── base_process.py        # Base process implementation
│   ├── heavyweight_process.py # Base heavyweight process
│   ├── heavyweight_a.py      # ProcessA implementation
│   ├── heavyweight_b.py      # ProcessB implementation
│   ├── lightweight_process.py # Base lightweight process
│   ├── lightweight_a.py      # Group A implementation (Lamport)
│   └── lightweight_b.py      # Group B implementation (Ricart-Agrawala)
└── algorithms/
    └── logical_clock.py  # Logical clock implementations
```

## Running the System

1. Clone the repository
2. Navigate to the project root directory
3. Run the system:
   ```bash
   python -m src.main
   ```

The system will:
1. Start ProcessA (with token)
2. Start ProcessB
3. Each heavyweight process will spawn its lightweight processes
4. The processes will coordinate access to the critical section (screen)
5. Each lightweight process will display its ID 10 times

## Output

The output will show the lightweight processes accessing the critical section (screen) in order:
```
I'm lightweight process A1
I'm lightweight process A1
...
I'm lightweight process A2
I'm lightweight process A2
...
I'm lightweight process A3
I'm lightweight process A3
...
I'm lightweight process B1
I'm lightweight process B1
...
```

## Stopping the System

Press Ctrl+C to gracefully shut down all processes.

## Implementation Details

### Token-based Mutual Exclusion
- Used between ProcessA and ProcessB
- ProcessA starts with the token
- Token is passed after all lightweight processes complete

### Lamport's Algorithm (Group A)
- Used by ProcessA's lightweight processes
- Uses Lamport's logical clocks
- Ensures total ordering of events

### Ricart-Agrawala's Algorithm (Group B)
- Used by ProcessB's lightweight processes
- Uses vector clocks
- Optimized version of Lamport's algorithm