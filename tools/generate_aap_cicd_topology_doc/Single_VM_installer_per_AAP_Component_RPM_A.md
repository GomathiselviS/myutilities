# Single VM installer per AAP Component RPM A

## Topology

```mermaid
%%{ init: { 'theme': 'default', 'graph': { 'htmlLabels': true }, 'themeVariables': { 'fontSize': '10px', 'nodePadding': '2px', 'edgeWidth': '1px' } } }%%
graph TB
  subgraph main[<b>Ansible Automation Platform</b>]
  subgraph id1[ ]
    id2([Gateway])
  end
  subgraph id3[Automation Mesh]
    subgraph id4[ ]
      id5([Controller])
    end
    id7([Execution Node])
  end
  subgraph id8[ ]
    id9([Automation Hub])
  end
  subgraph id10[ ]
    id11([EDA])
  end
  id12[(Managed Databse)]
 end
 rd[(Redis)]
id10-->id4
id1 <--> id3
id4-->id9
id1 & id9 & id11-->id12
id5<-->id7
id4 <--> id12
main --> rd
classDef title font-size:15px;
classDef db padding:10px;
class main title;
class rd db;
```

**_Legend:_**

```mermaid
%%{ init: { 'theme': 'default', 'graph': { 'htmlLabels': true }, 'themeVariables': { 'fontSize': '15px', 'nodePadding': '2px', 'edgeWidth': '1px' } } }%%
graph
  subgraph legend
    direction TB
   Y([ VM  ])
   Z[VM per component]
  end
classDef hide fill:#0000,stroke:#0000,stroke-width:0px;
classDef hide-font color:#0000;
class Y,legend hide-font;
class Z,legend hide;
```

## Description

The **Single VM installer per AAP Component RPM A** consists of the following:

| Component | VM count |
| --- | ----------- |
| AAP Gateway | 1 |
| Automation Controller | 1 |
| Hop Node | 1 |
| Automation Hub | 1 |
| Event Driven Ansible | 1 |
| Database (external) | 1 |
| Redis Cache (non-HA) | 1 |

## Inventory

```
```
