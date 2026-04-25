param location string
param containerAppName string
param containerImage string
param existingContainerAppsEnvironmentName string
param existingContainerAppsEnvironmentResourceGroup string
param identityId string
param identityClientId string
param acrLoginServer string
param storageAccountName string
param keyVaultIdentityId string
param defaultWorkspaceIdSecretUrl string
param defaultMaxOutputTokensSecretUrl string
param defaultRequestTimeoutSecondsSecretUrl string
param azureOpenAiDeploymentSecretUrl string
param azureOpenAiApiVersionSecretUrl string
param adminApiKeySecretUrl string
param cosmosEndpoint string
param azureOpenAiEndpoint string
param minReplicas int = 0
param maxReplicas int = 1
param tags object

resource existingEnv 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: existingContainerAppsEnvironmentName
  scope: resourceGroup(existingContainerAppsEnvironmentResourceGroup)
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: existingEnv.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
      }
      registries: [
        {
          server: acrLoginServer
          identity: identityId
        }
      ]
      secrets: [
        {
          name: 'default-workspace-id'
          keyVaultUrl: defaultWorkspaceIdSecretUrl
          identity: keyVaultIdentityId
        }
        {
          name: 'default-max-output-tokens'
          keyVaultUrl: defaultMaxOutputTokensSecretUrl
          identity: keyVaultIdentityId
        }
        {
          name: 'default-request-timeout-seconds'
          keyVaultUrl: defaultRequestTimeoutSecondsSecretUrl
          identity: keyVaultIdentityId
        }
        {
          name: 'azure-openai-deployment'
          keyVaultUrl: azureOpenAiDeploymentSecretUrl
          identity: keyVaultIdentityId
        }
        {
          name: 'azure-openai-api-version'
          keyVaultUrl: azureOpenAiApiVersionSecretUrl
          identity: keyVaultIdentityId
        }
        {
          name: 'admin-api-key'
          keyVaultUrl: adminApiKeySecretUrl
          identity: keyVaultIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: containerImage
          env: [
            {
              name: 'AzureWebJobsStorage__accountName'
              value: storageAccountName
            }
            {
              name: 'AzureWebJobsStorage__credential'
              value: 'managedidentity'
            }
            {
              name: 'AzureWebJobsStorage__clientId'
              value: identityClientId
            }
            {
              name: 'FUNCTIONS_WORKER_RUNTIME'
              value: 'python'
            }
            {
              name: 'AzureWebJobsFeatureFlags'
              value: 'EnableWorkerIndexing'
            }
            {
              name: 'USE_FAKE_AI'
              value: 'false'
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: identityClientId
            }
            {
              name: 'COSMOS_ENDPOINT'
              value: cosmosEndpoint
            }
            {
              name: 'COSMOS_DATABASE_NAME'
              value: 'ai-budget-db'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAiEndpoint
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT'
              secretRef: 'azure-openai-deployment'
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              secretRef: 'azure-openai-api-version'
            }
            {
              name: 'DEFAULT_WORKSPACE_ID'
              secretRef: 'default-workspace-id'
            }
            {
              name: 'DEFAULT_MAX_OUTPUT_TOKENS'
              secretRef: 'default-max-output-tokens'
            }
            {
              name: 'DEFAULT_REQUEST_TIMEOUT_SECONDS'
              secretRef: 'default-request-timeout-seconds'
            }
            {
              name: 'ADMIN_API_KEY'
              secretRef: 'admin-api-key'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

output id string = containerApp.id
output name string = containerApp.name
output fqdn string = containerApp.properties.configuration.ingress.fqdn
