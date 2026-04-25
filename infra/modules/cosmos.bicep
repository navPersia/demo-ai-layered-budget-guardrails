param location string
param accountName string
param databaseName string
param enableFreeTier bool = true
param databaseThroughput int = 1000
param principalId string
param tags object

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: accountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    enableFreeTier: enableFreeTier
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    disableLocalAuth: true
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: account
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
    options: {
      throughput: databaseThroughput
    }
  }
}

var containers = [
  'workspaces'
  'sessions'
  'usageEvents'
  'killSwitch'
]

resource sqlContainers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = [for containerName in containers: {
  parent: database
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        paths: [
          '/workspaceId'
        ]
        kind: 'Hash'
      }
    }
  }
}]

resource dataContributorRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: account
  name: guid(account.id, principalId, 'cosmos-data-contributor')
  properties: {
    principalId: principalId
    roleDefinitionId: '${account.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    scope: account.id
  }
}

output id string = account.id
output name string = account.name
output endpoint string = account.properties.documentEndpoint
