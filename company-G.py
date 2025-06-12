from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.onprem.client import User, Client
from diagrams.onprem.compute import Server
from diagrams.onprem.database import MariaDB, Mssql, Oracle, PostgreSQL
from diagrams.azure.compute import VM

# 이미지 경로 변수화
dyno_icon = "./images/salesforce/dyno.png"
connect_icon = "./images/salesforce/heroku-connect.png"
etl_icon = "./images/salesforce/integrate-io.png"
log_icon = "./images/salesforce/papertrail.png"
s3_icon = "./images/salesforce/hdrive.png"
data_cloud_icon = "./images/salesforce/data-cloud.png"
mkt_cloud_icon = "./images/salesforce/marketing-cloud.png"
svc_cloud_icon = "./images/salesforce/service-cloud.png"

with Diagram(
    "company-G Project",
    show=False,
    filename="company-G",
    node_attr={"fontsize": "14", "fontname": "Helvetica"},
    graph_attr = {"bgcolor": "transparent"}
):
    customer = User("Customer")

    # 고객사는 On-Premise와 Azure에 시스템을 운영하고 있음
    with Cluster("Company-G"):
        # On-Premise
        with Cluster("On-Premise"):
            oracle = Oracle("Oracle DB")
            onprem_proxy = Server("Proxy")

        # Azure
        with Cluster("Azure"):
            maria = MariaDB("MariaDB")
            mssql = Mssql("SQL Server")
            dashboard = Client("Dashboard")
            azure_proxy = VM("Proxy")

        # 고객 데이터는 각 시스템의 Legacy DB에 적재됨
        for db in [oracle, maria, mssql]:
            customer >> Edge(color="black") >> db
        
        # Legacy DB의 데이터는 Proxy Server를 통해 접근할 수 있음
        oracle >> Edge(color="blue") >> onprem_proxy
        maria >> Edge(color="blue") >> azure_proxy
        mssql >> Edge(color="blue") >> azure_proxy

    # 프로젝트를 통해 Data Hub와 이를 기반한 CDP, CRM, 대시보드를 구축하고자 함
    # Salesforce 시스템을 활용하여 구축
    with Cluster("Salesforce"):
        # Data Hub 구축을 위해 Heroku를 사용
        with Cluster("Heroku"):
            # 격리된 네트워크인 Private Space 환경
            with Cluster("Private Space"):
                postgres = PostgreSQL("Data Hub") # Heroku Postgres를 Data Hub로 활용

                # Data Hub의 데이터는 Proxy Server를 통해 접근할 수 있음
                proxy_dyno = Custom("Proxy", dyno_icon)
                proxy_dyno >> Edge(color="blue") >> postgres

                # Heroku Connect를 통해 Data Hub의 데이터와 Salesforce Service Cloud의 데이터를 연동
                heroku_connect = Custom("DB to CRM", connect_icon) 
                postgres >> Edge(color="red") >> heroku_connect
                
                api_dyno = Custom("API", dyno_icon) # Data Cloud의 데이터를 API를 활용해 추출하기 위한 애플리케이션 서버 구성

            # 3rd party addon은 Private Space 내부에 설치 불가능
            with Cluster("Externally Hosted"):
                # Heroku 내에 로깅 가능한 시스템을 Papertrail에 연결하여 통합 로깅 시스템 구성
                logging_service = Custom("Logging", log_icon)
                for src in [proxy_dyno, api_dyno, postgres, heroku_connect]:
                    src >> Edge(color="black") >> logging_service

                etl_tool = Custom("ETL", etl_icon) # Integrate.io를 활용한 ETL 파이프라인 구성

                s3_storage = Custom("Storage(S3)", s3_icon) # 당시 버전 기준 DB와 직접 연결이 불가능한 Data Cloud를 고려하여 HDrive를 활용한 AWS S3 구성

                # ETL 파이프라인 구성
                # 1. Legacy DB에서 Data Hub로 데이터 추출, 변환, 적재
                [onprem_proxy, azure_proxy] >> Edge(color="blue") >> etl_tool >> Edge(color="blue") >> proxy_dyno
                # 2. 가공, 집계 된 데이터를 타 시스템과 연동
                postgres >> Edge(color="red") >> proxy_dyno >> Edge(color="red") >> etl_tool
                # 2-1. 대시보드로 활용하기 위해 데이터 마트 구축 후 MariaDB에 적재
                # 2-2. 통합 회원 정보를 활용하기 위해 MariaDB에 적재
                etl_tool >> Edge(color="red") >> azure_proxy >> Edge(color="red") >> maria >> Edge(color="red") >> dashboard
                # 2-3. Data Cloud(CDP)에서 활용하기 위해 External Storage에 적재
                etl_tool >> Edge(color="red") >> s3_storage

        # CDP 구축을 위해 Data Cloud를 사용
        with Cluster("Data Cloud"):
            data_cloud = Custom("CDP", data_cloud_icon)
            s3_storage >> Edge(color="red") >> data_cloud # External Storage에 적재된 데이터 활용
            data_cloud >> Edge(color="blue") >> api_dyno >> Edge(color="blue") >> postgres # CDP에서 통합한 회원 정보를 API를 사용하여 추출 후 Data Hub에 적재

        # 개인화 마케팅을 위해 Marketing Cloud를 사용
        with Cluster("Marketing Cloud"):
            marketing_cloud = Custom("Marketing", mkt_cloud_icon)
        data_cloud >> Edge(color="red") >> marketing_cloud >> Edge(color="red") # CDP에서 생성한 세그먼트를 데이터를 기반으로 개인화 마케팅에 활용

        # CRM 구축을 위해 Service Cloud를 사용
        with Cluster("Service Cloud"):
            service_cloud = Custom("CRM", svc_cloud_icon)
        heroku_connect >> Edge(color="red") >> service_cloud >> Edge(color="red") # Heroku Connect를 통해 Data Hub의 데이터를 CRM과 연동