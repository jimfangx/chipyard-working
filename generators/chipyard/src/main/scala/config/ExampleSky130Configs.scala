package chipyard

import freechips.rocketchip.subsystem.{
  MBUS,
  WithCoherentBusTopology,
  WithExtMemSize,
  WithNMemoryChannels,
  WithNoMemPort
}
import org.chipsalliance.cde.config.Config
import testchipip.serdes.{
  DecoupledExternalSyncSerialPhyParams,
  ManagerRAMParams,
  SerialTLClientParams,
  SerialTLManagerParams,
  SerialTLParams,
  WithSerialTL
}
import testchipip.soc.{WithNoScratchpads, WithOffchipBus, WithOffchipBusClient}

/** Shared Sky130 tapeout configuration, excluding the processor tile choice. */
class SoCConfig extends Config(
  // TODO: Remove simulation collateral for the physical tapeout configuration.
  new chipyard.sky130.WithRealSky130EFCaravelPOR ++
  new chipyard.config.WithBroadcastManager ++
  new WithNoScratchpads ++
  new WithSerialTL(Seq(SerialTLParams(
    manager = Some(SerialTLManagerParams(
      memParams = Seq(ManagerRAMParams(
        address = BigInt("80000000", 16),
        size = BigInt("100000000", 16)
      )),
      isMemoryDevice = true
    )),
    client = Some(SerialTLClientParams()),
    phyParams = DecoupledExternalSyncSerialPhyParams(phitWidth = 1, flitWidth = 16)
  ))) ++
  new WithNoMemPort ++
  new WithNMemoryChannels(1) ++
  new chipyard.clocking.WithSingleClockBroadcastClockGenerator(freqMHz = 5) ++
  new WithOffchipBusClient(MBUS) ++
  new WithOffchipBus ++
  new chipyard.sky130.WithSky130EFIOCells(sim = false) ++
  new chipyard.sky130.WithSky130EFIOTotalCells(45) ++
  new WithExtMemSize(1L << 30) ++
  new WithCoherentBusTopology ++
  new chipyard.config.AbstractConfig)

class Sky130RocketConfig extends Config(
  new freechips.rocketchip.rocket.WithNSmallCores(1) ++
  new freechips.rocketchip.rocket.WithL1ICacheSets(64) ++
  new freechips.rocketchip.rocket.WithL1ICacheWays(1) ++
  new freechips.rocketchip.rocket.WithL1DCacheSets(64) ++
  new freechips.rocketchip.rocket.WithL1DCacheWays(1) ++
  new SoCConfig)

class Sky130ShuttleConfig extends Config(
  new shuttle.common.WithNShuttleCores ++
  new SoCConfig)
