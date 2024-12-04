import pulumi
from pulumi_azure_native import (
    cognitiveservices,
    containerregistry,
    # containerservice,
    documentdb,
    # insights,
    keyvault,
    # operationalinsights,
    resources,
    # search,
    storage,
)

config = pulumi.Config()
azure_config = pulumi.Config("azure-native")

# Resource Group provisioning
resource_group_args = resources.ResourceGroupArgs(
    location=azure_config.require("location"),
    resource_group_name=config.require("resource-group-name"),
)

resource_group = resources.ResourceGroup(
    resource_name=config.require("resource-group-name"),
    args=resource_group_args,
)

# Key Vault provisioning
vault = keyvault.Vault(
    resource_name=config.require("vault-name"),
    location=azure_config.require("location"),
    properties={
        "enable_rbac_authorization": True,
        "enable_soft_delete": True,
        "enabled_for_deployment": True,
        "enabled_for_disk_encryption": True,
        "enabled_for_template_deployment": True,
        "public_network_access": "Enabled",
        "sku": {
            "family": keyvault.SkuFamily.A,
            "name": keyvault.SkuName.STANDARD,
        },
        "soft_delete_retention_in_days": 90,
        "tenant_id": azure_config.require("tenantId"),
    },
    resource_group_name=resource_group.name,
    vault_name=config.require("vault-name"),
)

# Storage Account provisioning
storage_account_args = storage.StorageAccountArgs(
    location=azure_config.require("location"),
    kind=storage.Kind.STORAGE_V2,
    resource_group_name=resource_group.name,
    sku=storage.SkuArgs(name=storage.SkuName.STANDARD_LRS),
    account_name=config.require("storage-account-name"),
)

storage_account = storage.StorageAccount(
    resource_name=config.require("storage-account-name"),
    args=storage_account_args,
    opts=pulumi.ResourceOptions(parent=resource_group),
)

# Azure OpenAI provisioning
azure_open_ai_args = cognitiveservices.AccountArgs(
    resource_group_name=resource_group.name,
    location=config.require("openai-location"),
    account_name=config.require("openai-account-name"),
    kind="OpenAI",
    sku=cognitiveservices.SkuArgs(name="S0"),
    properties=cognitiveservices.AccountPropertiesArgs(
        custom_sub_domain_name=config.require("openai-domain-name"),
    ),
)
azure_open_ai = cognitiveservices.Account(
    resource_name=config.require("openai-account-name"),
    args=azure_open_ai_args,
    opts=pulumi.ResourceOptions(parent=resource_group),
)

# Azure OpenAI Text Embedding provisioning
text_embedding = cognitiveservices.Deployment(
    resource_name=config.require("openai-text-embedding-name"),
    account_name=azure_open_ai.name,
    deployment_name=config.require("openai-text-embedding-name"),
    properties={
        "model": {
            "format": "OpenAI",
            "name": config.require("openai-text-embedding-model"),
            "version": config.require("openai-text-embedding-version"),
        },
        "rai_policy_name": "Microsoft.DefaultV2",
        "version_upgrade_option": cognitiveservices.DeploymentModelVersionUpgradeOption.ONCE_NEW_DEFAULT_VERSION_AVAILABLE,
    },
    resource_group_name=resource_group.name,
    sku={
        "capacity": config.require_int("openai-text-embedding-capacity"),
        "name": "Standard",
    },
    opts=pulumi.ResourceOptions(parent=resource_group),
)

# Azure OpenAI LLM provisioning

llm = cognitiveservices.Deployment(
    resource_name=config.require("openai-llm-name"),
    account_name=azure_open_ai.name,
    deployment_name=config.require("openai-llm-name"),
    properties={
        "model": {
            "format": "OpenAI",
            "name": config.require("openai-llm-model"),
            "version": config.require("openai-llm-version"),
        },
        "rai_policy_name": "Microsoft.DefaultV2",
        "version_upgrade_option": cognitiveservices.DeploymentModelVersionUpgradeOption.ONCE_CURRENT_VERSION_EXPIRED,
    },
    resource_group_name=resource_group.name,
    sku={
        "capacity": config.require_int("openai-llm-capacity"),
        "name": "GlobalStandard",
    },
    opts=pulumi.ResourceOptions(parent=resource_group),
)

# Container Registry provisioning

container_registry = containerregistry.Registry(
    resource_name=config.require("container-registry-resource-name"),
    admin_user_enabled=True,
    data_endpoint_enabled=False,
    encryption={
        "status": containerregistry.EncryptionStatus.DISABLED,
    },
    location=azure_config.require("location"),
    network_rule_bypass_options=containerregistry.NetworkRuleBypassOptions.AZURE_SERVICES,
    policies={
        "export_policy": {
            "status": containerregistry.ExportPolicyStatus.ENABLED,
        },
        "quarantine_policy": {
            "status": containerregistry.PolicyStatus.DISABLED,
        },
        "retention_policy": {
            "days": 7,
            "status": containerregistry.PolicyStatus.DISABLED,
        },
        "trust_policy": {
            "status": containerregistry.PolicyStatus.DISABLED,
            "type": containerregistry.TrustPolicyType.NOTARY,
        },
    },
    public_network_access=containerregistry.PublicNetworkAccess.ENABLED,
    registry_name=config.require("container-registry-name"),
    resource_group_name=resource_group.name,
    sku={
        "name": containerregistry.SkuName.BASIC,
    },
    zone_redundancy=containerregistry.ZoneRedundancy.DISABLED,
    opts=pulumi.ResourceOptions(parent=resource_group),
)

# MongoDB RU provisioning

mongo_db = documentdb.DatabaseAccount(
    resource_name=config.require("mongodb-resource-name"),
    account_name=config.require("mongodb-account-name"),
    analytical_storage_configuration={
        "schema_type": documentdb.AnalyticalStorageSchemaType.FULL_FIDELITY,
    },
    api_properties={
        "server_version": "7.0",
    },
    backup_policy={
        "continuous_mode_properties": {
            "tier": documentdb.ContinuousTier.CONTINUOUS7_DAYS,
        },
        "type": "Continuous",
    },
    capabilities=[
        {
            "name": "EnableMongo",
        },
        {
            "name": "EnableServerless",
        },
    ],
    capacity={
        "total_throughput_limit": 4000,
    },
    consistency_policy={
        "default_consistency_level": documentdb.DefaultConsistencyLevel.SESSION,
        "max_interval_in_seconds": 5,
        "max_staleness_prefix": 100,
    },
    create_mode=documentdb.CreateMode.DEFAULT,
    database_account_offer_type=documentdb.DatabaseAccountOfferType.STANDARD,
    default_identity="FirstPartyIdentity",
    disable_key_based_metadata_write_access=False,
    disable_local_auth=False,
    enable_analytical_storage=False,
    enable_automatic_failover=False,
    enable_free_tier=False,
    enable_multiple_write_locations=False,
    enable_partition_merge=False,
    identity={
        "type": documentdb.ResourceIdentityType.NONE,
    },
    is_virtual_network_filter_enabled=False,
    kind=documentdb.DatabaseAccountKind.MONGO_DB,
    location=azure_config.require("location"),
    locations=[
        {
            "failover_priority": 0,
            "is_zone_redundant": False,
            "location_name": azure_config.require("location"),
        }
    ],
    minimal_tls_version=documentdb.MinimalTlsVersion.TLS12,
    network_acl_bypass=documentdb.NetworkAclBypass.NONE,
    public_network_access=documentdb.PublicNetworkAccess.ENABLED,
    resource_group_name=resource_group.name,
    tags={
        "defaultExperience": "Azure Cosmos DB for MongoDB API",
        "hidden-cosmos-mmspecial": "",
    },
)

# # MongoDB Database provisioning
#
# agent_memory_db = documentdb.MongoDBResourceMongoDBDatabase(
#     resource_name="MongoDB-Agent-DB",
#     account_name=mongo_db.name,
#     database_name="agent",
#     location="Sweden Central",
#     resource={"id": "agent"},
#     resource_group_name=resource_group.name,
# )
#
# # MongoDB Checkpoints Collection provisioning
#
# agent_memory_collection = documentdb.MongoDBResourceMongoDBCollection(
#     resource_name="MongoDB-Agent-Checkpoints-Collection",
#     account_name=mongo_db.name,
#     database_name="agent",
#     collection_name="checkpoints",
#     location="Sweden Central",
#     resource={
#         "id": "checkpoints",
#     },
#     resource_group_name=resource_group.name,
# )
#
# # Azure AI Search provisioning
#
# ai_search = search.Service(
#     resource_name="AI-Search-Dev",
#     disable_local_auth=False,
#     encryption_with_cmk={
#         "enforcement": search.SearchEncryptionWithCmk.UNSPECIFIED,
#     },
#     hosting_mode=search.HostingMode.DEFAULT,
#     location="North Europe",
#     network_rule_set={
#         "ip_rules": [
#             {
#                 "value": "195.87.22.4",
#             },
#             {
#                 "value": "31.223.98.197",
#             },
#         ],
#     },
#     partition_count=1,
#     public_network_access=search.PublicNetworkAccess.ENABLED,
#     replica_count=1,
#     resource_group_name=resource_group.name,
#     search_service_name="ai-search-rag-product-dev",
#     sku={
#         "name": search.SkuName.BASIC,
#     },
# )
#
# # Log Analytics Workspace provisioning
#
# law_rag_product_dev = operationalinsights.Workspace(
#     resource_name="LAW-RAG-Product-Dev",
#     features={
#         "enable_log_access_using_only_resource_permissions": True,
#     },
#     location="swedencentral",
#     public_network_access_for_ingestion=operationalinsights.PublicNetworkAccessType.ENABLED,
#     public_network_access_for_query=operationalinsights.PublicNetworkAccessType.ENABLED,
#     resource_group_name=resource_group.name,
#     retention_in_days=30,
#     sku={
#         "name": "pergb2018",
#     },
#     workspace_capping={
#         "daily_quota_gb": -1,
#     },
#     workspace_name="LAW-RAG-Product-Dev",
#     opts=pulumi.ResourceOptions(protect=True),
# )
#
# # AI Search Diagnostic Settings
#
# ai_search_diagnostic_setting = insights.DiagnosticSetting(
#     resource_name="AI-Search-Diagnostic-Setting",
#     logs=[
#         {
#             "category_group": "audit",
#             "enabled": True,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category_group": "allLogs",
#             "enabled": True,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#     ],
#     metrics=[
#         {
#             "category": "AllMetrics",
#             "enabled": True,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         }
#     ],
#     name="LAW-RAG-Product-Dev-Diagnostic-Setting",
#     resource_uri=ai_search.id,
#     workspace_id=law_rag_product_dev.id,
# )
#
# # Storage Account Diagnostic Settings
#
# storage_account_diagnostic_setting = insights.DiagnosticSetting(
#     resource_name="Storage-Account-Diagnostic-Setting",
#     metrics=[
#         {
#             "category": "Transaction",
#             "enabled": True,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category": "Capacity",
#             "enabled": False,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#     ],
#     name="LAW-RAG-Product-Dev-Diagnostic-Setting",
#     resource_uri=storage_account.id,
#     workspace_id=law_rag_product_dev.id,
# )
#
# # MongoDB Diagnostic Settings
#
# mongo_db_diagnostic_setting = insights.DiagnosticSetting(
#     resource_name="MongoDB-Diagnostic-Setting",
#     log_analytics_destination_type="Dedicated",
#     logs=[
#         {
#             "category": "DataPlaneRequests",
#             "enabled": True,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category": "MongoRequests",
#             "enabled": True,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category": "QueryRuntimeStatistics",
#             "enabled": True,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category": "PartitionKeyStatistics",
#             "enabled": False,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category": "PartitionKeyRUConsumption",
#             "enabled": False,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category": "ControlPlaneRequests",
#             "enabled": True,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category": "CassandraRequests",
#             "enabled": False,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category": "GremlinRequests",
#             "enabled": False,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category": "TableApiRequests",
#             "enabled": False,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#     ],
#     metrics=[
#         {
#             "category": "SLI",
#             "enabled": False,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category": "Requests",
#             "enabled": False,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#     ],
#     name="LAW-RAG-Product-Dev-Diagnostic-Setting",
#     resource_uri=mongo_db.id,
#     workspace_id=law_rag_product_dev.id,
# )
#
# # OpenAI Diagnostic Settings
#
# open_ai_diagnostic_setting = insights.DiagnosticSetting(
#     resource_name="OpenAI-Diagnostic-Setting",
#     logs=[
#         {
#             "category_group": "Audit",
#             "enabled": True,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#         {
#             "category_group": "allLogs",
#             "enabled": True,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         },
#     ],
#     metrics=[
#         {
#             "category": "AllMetrics",
#             "enabled": False,
#             "retention_policy": {
#                 "days": 0,
#                 "enabled": False,
#             },
#         }
#     ],
#     name="LAW-RAG-Product-Dev-Diagnostic-Setting",
#     resource_uri=azure_open_ai.id,
#     workspace_id=law_rag_product_dev.id,
# )
#
#
# # AKS Cluster provisioning
#
# aks_rag_product_dev = containerservice.ManagedCluster(
#     resource_name="AKS-RAG-Product-Dev",
#     addon_profiles={
#         "azureKeyvaultSecretsProvider": {
#             "enabled": False,
#         },
#         "azurepolicy": {
#             "enabled": False,
#         },
#     },
#     agent_pool_profiles=[
#         {
#             "count": 1,
#             "enable_auto_scaling": True,
#             "enable_fips": False,
#             "enable_node_public_ip": False,
#             "kubelet_disk_type": containerservice.KubeletDiskType.OS,
#             "max_count": 1,
#             "max_pods": 110,
#             "min_count": 1,
#             "mode": containerservice.AgentPoolMode.SYSTEM,
#             "name": "agentpool",
#             "orchestrator_version": "1.29.8",
#             "os_disk_size_gb": 128,
#             "os_disk_type": containerservice.OSDiskType.MANAGED,
#             "os_sku": containerservice.OSSKU.UBUNTU,
#             "os_type": containerservice.OSType.LINUX,
#             "power_state": {
#                 "code": containerservice.Code.RUNNING,
#             },
#             "type": containerservice.AgentPoolType.VIRTUAL_MACHINE_SCALE_SETS,
#             "upgrade_settings": {
#                 "max_surge": "10%",
#             },
#             "vm_size": "Standard_D4s_v3",
#         }
#     ],
#     auto_scaler_profile={
#         "balance_similar_node_groups": "false",
#         "expander": containerservice.Expander.RANDOM,
#         "max_empty_bulk_delete": "10",
#         "max_graceful_termination_sec": "600",
#         "max_node_provision_time": "15m",
#         "max_total_unready_percentage": "45",
#         "new_pod_scale_up_delay": "0s",
#         "ok_total_unready_count": "3",
#         "scale_down_delay_after_add": "10m",
#         "scale_down_delay_after_delete": "10s",
#         "scale_down_delay_after_failure": "3m",
#         "scale_down_unneeded_time": "10m",
#         "scale_down_unready_time": "20m",
#         "scale_down_utilization_threshold": "0.5",
#         "scan_interval": "10s",
#         "skip_nodes_with_local_storage": "false",
#         "skip_nodes_with_system_pods": "true",
#     },
#     auto_upgrade_profile={
#         "upgrade_channel": containerservice.UpgradeChannel.PATCH,
#     },
#     disable_local_accounts=False,
#     dns_prefix="AKS-RAG-Product-Dev",
#     enable_rbac=True,
#     identity={
#         "type": containerservice.ResourceIdentityType.SYSTEM_ASSIGNED,
#     },
#     kubernetes_version="1.29.8",
#     location="swedencentral",
#     network_profile={
#         "dns_service_ip": "10.0.0.10",
#         "ip_families": [containerservice.IpFamily.I_PV4],
#         "load_balancer_profile": {
#             "effective_outbound_ips": [
#                 {
#                     "id": "/subscriptions/6f41d85d-e8e3-4b42-aee3-205408d7dbd8/resourceGroups/MC_RG-CorporateAI-RAG-Product-Dev_AKS-RAG-Product-Dev_swedencentral/providers/Microsoft.Network/publicIPAddresses/454e9ceb-117c-44df-93f2-3e771b7c1c65",
#                 }
#             ],
#             "managed_outbound_ips": {
#                 "count": 1,
#             },
#         },
#         "load_balancer_sku": "Standard",
#         "network_dataplane": containerservice.NetworkDataplane.AZURE,
#         "network_plugin": containerservice.NetworkPlugin.AZURE,
#         "network_plugin_mode": containerservice.NetworkPluginMode.OVERLAY,
#         "outbound_type": containerservice.OutboundType.LOAD_BALANCER,
#         "pod_cidr": "10.244.0.0/16",
#         "pod_cidrs": ["10.244.0.0/16"],
#         "service_cidr": "10.0.0.0/16",
#         "service_cidrs": ["10.0.0.0/16"],
#     },
#     node_resource_group="MC_RG-CorporateAI-RAG-Product-Dev_AKS-RAG-Product-Dev_swedencentral",
#     oidc_issuer_profile={
#         "enabled": False,
#     },
#     resource_group_name=resource_group.name,
#     resource_name_="AKS-RAG-Product-Dev",
#     service_principal_profile={
#         "client_id": "msi",
#     },
#     sku={
#         "name": containerservice.ManagedClusterSKUName.BASE,
#         "tier": containerservice.ManagedClusterSKUTier.FREE,
#     },
#     storage_profile={
#         "disk_csi_driver": {
#             "enabled": True,
#         },
#         "file_csi_driver": {
#             "enabled": True,
#         },
#         "snapshot_controller": {
#             "enabled": True,
#         },
#     },
#     support_plan=containerservice.KubernetesSupportPlan.KUBERNETES_OFFICIAL,
#     opts=ResourceOptions(replace_on_changes=["*"], delete_before_replace=True),
# )
