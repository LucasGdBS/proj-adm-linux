## Arquitetura

A infraestrutura deve conter os seguintes componentes interconectados:

·  
Proxy Reverso e Load Balancer: Um contêiner Nginx
configurado para balancear carga entre duas instâncias da aplicação.

·  
Camada de Aplicação: Duas instâncias idênticas
da mesma aplicação rodando em contêineres separados.

·  
Base de Dados: Um contêiner de banco de dados
com Volumes para persistência.

·  
Monitoramento: Um contêiner Prometheus coletando
métricas e um Grafana para visualização.

## Requisitos Técnicos

A. Configuração de Rede e Portas

Não exponham o Banco de Dados para fora do host de execução.
Apenas o Nginx deve ter a porta pública (Ex: 80 ou 8080).

Criem uma rede interna no Compose onde os contêineres se
comunicam internamente.

B. Persistência e Segurança

Os dados do banco não podem sumir se o contêiner for
deletado.

Configurarem volumes mapeando diretórios do host para o
banco de dados.

Se estiverem usando Red Hat/Podman, devem lidar com o
SELinux para solucionar problemas de acesso aos arquivos.

C. Scripts de Inicialização

Criem um script start-infra.sh que valide se o Docker/Podman
está rodando, suba o ambiente com docker-compose up -d e exiba o status dos
processos (verifiquem também como o script se comporta caso o ambiente já esteja
em execução).
