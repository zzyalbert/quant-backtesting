# event-driven-backtesting
This is a event-driven backtesting framework. 

### Components  
The framework contains the following components:
 - `DataHandler`
 - `Strategy`
 - `Portfolio`
 - `ExecutionHandler`
 - `Performance`
 - `Backtest` and `Event`
 
### Events
`DataHandler`:      output `MarketEvent`

`Strategy`:         input `MarketEvent`, output `SignalEvent`

`Portfolio`:        input `MarketEvent`, `FillEvent`, `SignalEvent`, output `OrderEvent`

`ExecutionHandler`: input `OrderEvent`, output `FillEvent`

`Performance`:      used by `Portfolio` to evaluate `Strategy`