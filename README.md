# Projeto Mottag

## Introdução

O **Projeto Mottag** está sendo desenvolvido para a empresa brasileira **Mottu**, referência em aluguel de motocicletas. O projeto tem como objetivo criar uma solução tecnológica para melhorar a gestão das motos dentro dos pátios da empresa. Por meio de um sistema de localização inteligente, busca-se reduzir perdas, otimizar processos e oferecer mais agilidade e eficiência aos operadores.

---

## Autores

Desenvolvido por **Grupo LLM** para o **Challenge FIAP 2025**:

- Gabriel Marques de Lima Sousa – RM 554889
- Leonardo Matheus Teixeira – RM 556629
- Leonardo Menezes Parpinelli Ribas – RM 557908

---

## Problema Identificado

Atualmente, a Mottu enfrenta dificuldades significativas para controlar e localizar suas motos dentro dos pátios. O sistema atual depende de registros manuais de entrada e saída, aliado ao uso de rastreadores GPS com autonomia limitada. Isso gera uma série de problemas operacionais:

- **Risco de perda de ativos:** motocicletas podem sair do pátio sem registro adequado, especialmente se o rastreador estiver descarregado ou for removido.
- **Dificuldade de localização:** encontrar uma moto no pátio pode levar até dois dias.
- **Inventários demorados:** é necessário refazer inventários frequentemente, consumindo tempo e recursos.
- **Ativos “invisíveis”:** motos paradas por problemas técnicos ou outras irregularidades podem permanecer no pátio sem visibilidade no sistema.
- **Baixa precisão em ambientes internos:** o GPS não oferece confiabilidade suficiente em áreas cobertas ou fechadas.

**Premissa importante:** os operadores já utilizam smartphones corporativos no dia a dia da operação, o que viabiliza a adoção da solução sem exigir novos dispositivos móveis.

---

## Solução Proposta

O **Mottag** busca resolver esses desafios com a adoção de **tags BLE (Bluetooth Low Energy)**, que são acopladas às motos enquanto elas estiverem no pátio. Assim que a moto sai, a tag é retirada, já que fora do pátio o rastreador GPS atual continua sendo suficiente.

**Funcionamento em etapas:**

1. Ao entrar no pátio, a moto recebe uma **tag** que passa a ser monitorada.
2. No aplicativo mobile, o operador pode visualizar um **mapa digital detalhado**, em “near real time” (atraso máximo de 30 segundos), mostrando a posição aproximada das motos, das antenas e dos próprios operadores.
3. Caso precise localizar uma moto específica, o operador pode acionar a tag para que ela **pisque uma luz e emita um som**, facilitando a busca no “last mile”.

> Apesar de já aproveitar os smartphones em uso, o sistema opera em um aplicativo próprio, que no futuro poderá ser integrado ao app já existente da Mottu.

---

## Detalhes Técnicos

- **Tag BLE:** duas versões disponíveis:
    1. Beacon BLE simples.
    2. Beacon BLE com sinal luminoso e sonoro.
- **Mapeamento com antenas:**
    - As antenas são dispositivos **ESP32** que realizam varreduras constantes dos sinais BLE.
    - Para cobrir todo o ambiente, a ideia é posicionar uma antena em cada vértice de um “retângulo virtual” que representa o espaço.
    - Em pátios maiores ou ambientes com obstáculos (como paredes), antenas adicionais são posicionadas ao redor para garantir cobertura completa.
- **Comunicação e processamento:**
    - As antenas enviam os dados de escaneamento para um **MQTT broker**.
    - Uma **API Java** recebe as mensagens do broker, processa os dados e atualiza o estado das motos e antenas.
    - O **dashboard web**, desenvolvido com **Thymeleaf**, exibe o mapa interativo e os dados em tempo real.
- **Posicionamento do operador:** o próprio smartphone emite sinal BLE, permitindo que o sistema mostre em tempo real a localização do operador dentro do mapa.

---

## Funcionalidades Adicionais

Além da localização, o sistema contará com:

- **Dashboard administrativo:** para edição do mapa, cadastro de usuários e acompanhamento de dispositivos.
- **Chatbot integrado ao aplicativo:** suporte rápido para orientar operadores em tarefas e dúvidas.
- **Inteligência Artificial:** análise de dados coletados, geração de insights e sugestões para otimização da operação dos pátios.
- **Controle de saída com RFID:** integração de etiquetas RFID nas tags, em conjunto com portais de monitoramento, para prevenir saídas indevidas das motos ou tags.

---

## Resultados

Com a implementação do **Mottag**, já foi possível comprovar o funcionamento do sistema de forma integrada, desde a coleta dos dados pelas antenas até a exibição no mapa web. Entre os principais resultados observados estão:

- **Detecção e rastreamento BLE confiável**, com atualização contínua das posições das motos no dashboard.
- **Processamento em tempo quase real** via MQTT e API Java, garantindo latência mínima.
- **Interface web responsiva**, permitindo o acompanhamento das motos, operadores e antenas com clareza e filtros customizados.
- **Ativação remota de buzzer e LED** nas tags, facilitando a localização física das motos.
- **Arquitetura modular e escalável**, preparada para novos pátios e futuras integrações com sistemas internos da Mottu.

Esses resultados demonstram a viabilidade técnica e operacional da solução, abrindo caminho para sua expansão em larga escala nos pátios da empresa.

---

## Observações Importantes

- As **tags são utilizadas apenas dentro dos pátios**, não acompanhando as motos quando saem.
- O **mapa digital** é completo e detalhado, com filtros que permitem exibir apenas motos, apenas operadores ou apenas antenas.
- A **atualização em near real time** (até 30 segundos de atraso) garante visibilidade contínua sem sobrecarregar a rede ou os dispositivos.

---

Link do repositório da API Java: https://github.com/TeamLLMTech/mottag-backend-java