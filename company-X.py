from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server
from diagrams.onprem.database import MariaDB, Mssql, Oracle, PostgreSQL
from diagrams.onprem.queue import Kafka
from diagrams.azure.compute import VM

# 이미지 경로 변수화
dyno_icon = "./images/salesforce/dyno.png"
connect_icon = "./images/salesforce/heroku-connect.png"
log_icon = "./images/salesforce/papertrail.png"
svc_cloud_icon = "./images/salesforce/service-cloud.png"

with Diagram(
    "company-X Project",
    show=False,
    filename="company-X",
    node_attr={"fontsize": "14", "fontname": "Helvetica"},
    graph_attr = {"bgcolor": "transparent"}
):
    customer = User("Customer")

    # 고객사는 On-Premise와 Azure에 시스템을 운영하고 있음
    with Cluster("Company-G"):
        # On-Premise
        with Cluster("On-Premise"):
            oracle = Oracle("Oracle DB")
            onprem_proxy = Server("Proxy, Kafka Connect") # 프록시 서버의 목적 외에도 Legacy DB의 변경 데이터를 캡쳐할 수 있는 Kafka Connect 설치

        # Azure
        with Cluster("Azure"):
            maria = MariaDB("MariaDB")
            mssql = Mssql("SQL Server")
            azure_proxy = VM("Proxy, Kafka Connect") # 프록시 서버의 목적 외에도 Legacy DB의 변경 데이터를 캡쳐할 수 있는 Kafka Connect 설치

        # 고객 데이터는 각 시스템의 Legacy DB에 적재됨
        for db in [oracle, maria, mssql]:
            customer >> Edge(color="black") >> db
        
        # Legacy DB의 데이터는 Proxy Server를 통해 접근할 수 있음
        oracle >> Edge(color="blue") >> onprem_proxy
        [maria, mssql] >> Edge(color="blue") >> azure_proxy

    # 프로젝트를 통해 Data Hub와 이를 기반한 CRM을 구축하고자 함
    # Salesforce 시스템을 활용하여 구축
    with Cluster("Salesforce"):
        # Data Hub 구축을 위해 Heroku를 사용
        with Cluster("Heroku"):
            # 격리된 네트워크인 Private Space 환경
            with Cluster("Private Space"):
                postgres = PostgreSQL("Data Hub") # Heroku Postgres를 Data Hub로 활용
                kafka = Kafka("Kafka") # Heroku Kafka를 설치하여 CDC 구성
                connect_dyno = Custom("Kafka Connect", dyno_icon) # Kafka, Data Hub와 통신하기 위한 애플리케이션 서버 구성
                transform_dyno = Custom("Transform", dyno_icon) # 데이터 가공 및 통합을 위한 애플리케이션 서버 구성
                
                # CDC 파이프라인 구성
                # 1. Legacy DB의 변경 데이터를 Debezium Source Connector를 사용하여 수집하여 Kafka에 적재, 적재된 메세지를 Debezium Sink Connector를 사용하여 Data Hub에 반영
                [onprem_proxy, azure_proxy] >> Edge(color="blue") >> kafka >> Edge(color="blue") >> connect_dyno >> Edge(color="blue") >> postgres
                # 2. 데이터 가공 및 통합 진행
                # 2-1. 1에서 반영된 데이터에서 가공이 필요한 데이터를 선별하고 Heroku Streaming Data Connector를 사용해 Kafka에 적재 
                postgres >> Edge(color="brown") >> kafka
                # 2-2. Transform Dyno에서 Kafka의 메세지를 읽어와 Python 스크립트를 활용하여 데이터 가공 및 통합 진행
                kafka >> Edge(color="brown") >> transform_dyno
                # 2-3. 전처리가 완료된 데이터를 Data Hub에 적재하기 위해 Kafka에 적재, 적재된 메세지는 1번과 동일한 방식으로 Data Hub에 반영
                transform_dyno >> Edge(color="brown") >> kafka
                # 3. 가공, 집계 된 데이터를 타 시스템과 연동
                # 통합 회원 정보를 활용하기 위해 Kafka에 적재된 메세지를 Debezium Sink Connector를 사용하여 MariaDB에 반영
                kafka >> Edge(color="red") >> azure_proxy >> Edge(color="red") >> maria

                # Heroku Connect를 통해 Data Hub의 데이터와 Salesforce Service Cloud의 데이터를 연동
                heroku_connect = Custom("DB to CRM", connect_icon) 
                postgres >> Edge(color="red") >> heroku_connect

            # 3rd party addon은 Private Space 내부에 설치 불가능
            with Cluster("Externally Hosted"):
                # Heroku 내에 로깅 가능한 시스템을 Papertrail에 연결하여 통합 로깅 시스템 구성
                logging_service = Custom("Logging", log_icon)
                for src in [connect_dyno, transform_dyno, postgres, heroku_connect, kafka]:
                    src >> Edge(color="black") >> logging_service

        # CRM 구축을 위해 Service Cloud를 사용
        with Cluster("Service Cloud"):
            service_cloud = Custom("CRM", svc_cloud_icon)
        heroku_connect >> Edge(color="red") >> service_cloud >> Edge(color="red") # Heroku Connect를 통해 Data Hub의 데이터를 CRM과 연동