# Expansão futura

Prioridades técnicas:

1. Extrair telas e formulários de `app.py` por domínio, mantendo callbacks e contratos; acrescentar type hints nas fronteiras. Evitar uma reescrita total que misture organização com migração dos dados.
2. Centralizar validadores dos demais cadastros no domínio; adicionar índices somente após medir consultas com histórico longo.
3. Criar fontes de edital versionadas, rastreáveis e separadas da curadoria pedagógica. A ordem sugerida não deve virar bloqueio obrigatório.
4. Expandir acessibilidade, foco por teclado e leitor de tela; medir contraste e layouts menores em ambos os temas.
5. Planejar assinatura de código e builds em runner Windows com dependências auditadas. Linux precisa de validação própria.

Restrições: offline, poucas dependências de runtime, baixo consumo de RAM, nenhuma thread/processo ocioso para animação. Não inventar dados nos gráficos nem mexer em métricas reais para demonstração. Não impor agenda rígida ou usar metas como punição.

Banco pessoal, instalação e estado de autenticação são contextos locais; não copiá-los para documentação versionada. Qualquer sync, conta, backend ou telemetria altera o modelo de segurança e exige discussão explícita com o usuário.
