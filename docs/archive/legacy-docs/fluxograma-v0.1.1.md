# Fluxograma DEMAS v0.1.1

```mermaid
flowchart TD
    subgraph INICIALIZAÇÃO["🎯 Inicialização da Aplicação"]
        A1["📱 main()"] --> A2["🚀 SimulationApp()"]
        A2 --> A3["📞 on_mount()"]
    end

    subgraph SETUP["⚙️ Setup da Simulação"]
        A3 --> B1["🔄 reset_simulation()"]
        B1 --> B2["📦 SimulationRunner.reset(seed)"]
        
        B2 --> B3["⚡ Kernel(seed)"]
        B3 --> B4["🟢 Oracle(r_bar, kappa, sigma)"]
        B4 --> B5["🏛️ ExchangeAgent(id=0)"]
        B5 --> B6["📝 kernel.register(exchange)"]
    end

    subgraph AGENTES["👥 Registro dos Agentes"]
        B6 --> C1["🤖 Market Makers (5x)"]
        C1 --> C2["📝 register() + wakeup(at_time=1)"]
        
        C2 --> C3["📊 Informed Traders (10x)"]
        C3 --> C4["📝 register() + wakeup(at_time=1)"]
        
        C4 --> C5["💧 Liquidity Trader (1x BUY)"]
        C5 --> C6["📝 register() + wakeup(at_time=1)"]
        
        C6 --> C7["🔊 Noise Traders (20x)"]
        C7 --> C8["📝 register() + wakeup(at_time=1)"]
    end

    subgraph LATENCIA["🌐 Configuração de Latências"]
        C8 --> D1["⏱️ Para cada par de agentes"]
        D1 --> D2["📏 latency = rand(1, 10)"]
        D2 --> D3["💾 kernel.set_latency(src, dst, delay)"]
    end

    subgraph UI["🖥️ Interface Textual (TUI)"]
        D3 --> E1["📊 PriceChart"]
        E1 --> E2["📋 Order Book Table"]
        E2 --> E3["💰 Trades Table"]
        E3 --> E4["📜 Events Log Table"]
        E4 --> E5["📈 Stats Panel"]
    end

    subgraph LOOP["🔄 Loop Principal de Simulação"]
        F1{"▶️ Simulation\nRunning?"} -->|Sim| F2["⏰ Timer tick()\n(0.1s)"]
        F1 -->|Não| F3["⏹️ Pausado"]
        
        F2 --> F4["🔁 Para cada step (20x)"]
        F4 --> F5{"❓ kernel.step()"}
        
        F5 -->|True| F6["📤 get_state()"]
        F5 -->|False| F7["⏹️ Parar simulação"]
        
        F6 --> F8["🖼️ update_ui()"]
        F8 --> F1
    end

    subgraph KERNEL_STEP["⚡ Kernel Step - Ciclo de Eventos"]
        K1["📥 Pop evento\n(heapq.heappop)"] --> K2{"❓ Evento\nexiste?"}
        K2 -->|Não| K3["🔴 running = False"]
        K2 -->|Sim| K4["⏱️ time = when"]
        
        K4 --> K5{"📬 kind ==\nWAKEUP?"}
        K5 -->|Sim| K6["📞 agent.wakeup(time)"]
        K5 -->|Não| K7["📩 agent.receive(msg)"]
        
        K6 --> K8["📤 Mensagem\nprocessada"]
        K7 --> K8
        
        K8 --> K9["📝 _record_event()\n(PROCESSED)"]
        K9 --> K10["🔄 Próximo step"]
    end

    subgraph AGENT_LIFECYCLE["🔵 Ciclo de Vida do Agente"]
        L1["⏰ wakeup(now)"] --> L2["🤔 Decisão de trading"]
        L2 --> L3["📤 kernel.send()\n(ordem)"]
        L3 --> L4["⏳ Aguarda próximo\nWAKEUP"]
        
        M1["📥 receive(msg)"] --> M2{"📬 tipo da\nmensagem?"}
        M2 -->|"ORDER"| M3["📊 Processar ordem"]
        M2 -->|"CANCEL"| M4["❌ Cancelar ordem"]
        M2 -->|"QUERY"| M5["🔍 Consultar estado"]
        M2 -->|"ACK"| M6["✅ Confirmar ação"]
        
        M3 --> M7["📤 Resposta/ação"]
        M4 --> M7
        M5 --> M7
        M6 --> M7
    end

    F4 -.-> K1
    
    style INICIALIZAÇÃO fill:#e1f5fe
    style SETUP fill:#e8f5e8
    style AGENTES fill:#fff3e0
    style LATENCIA fill:#fce4ec
    style UI fill:#f3e5f5
    style LOOP fill:#e0f7fa
    style KERNEL_STEP fill:#fff8e1
    style AGENT_LIFECYCLE fill:#e8eaf6
```

## Legenda

| Símbolo | Significado |
|---------|-------------|
| 📱 | Ponto de entrada |
| ⚙️ | Configuração |
| 👥 | Registro de agentes |
| 🌐 | Rede/Comunicação |
| 🖥️ | Interface TUI |
| 🔄 | Loop principal |
| ⚡ | Processamento de eventos |
| 🔵 | Comportamento do agente |

## Fluxo Principal

1. **Inicialização**: `main()` → `SimulationApp` → `on_mount()`
2. **Setup**: Criação do Kernel, Oracle, Exchange e todos os agentes
3. **Execução**: Loop de simulação processando eventos através do Kernel
4. **Interface**: Atualização visual a cada tick (0.1s)
