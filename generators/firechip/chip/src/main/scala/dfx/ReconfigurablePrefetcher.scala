package firechip.dfx

import chisel3._
import org.chipsalliance.cde.config.{Config, Parameters}
import barf.{AbstractPrefetcher, CanInstantiatePrefetcher, TLPrefetcherKey}

/** A stable DFX partition boundary for any bar-fetchers TL prefetcher.
  *
  * The inner prefetcher is deliberately held as an unconditional Module. This
  * preserves the physical hierarchy that Vivado needs even when firtool would
  * otherwise inline the implementation. The wrapper's PrefetcherIO is the
  * base/RM interface contract; address and cache parameters must therefore be
  * unchanged for all RMs made against a base shell.
  */
class ReconfigurablePrefetcher(params: CanInstantiatePrefetcher)
    (implicit p: Parameters) extends AbstractPrefetcher with DfxReconfigurableWrapper {
  val wrapperName = "ReconfigurablePrefetcher"
  val inner = params.instantiate()(p)
  io <> inner.io
}

case class ReconfigurablePrefetcherParams(inner: CanInstantiatePrefetcher)
    extends CanInstantiatePrefetcher {
  def desc = s"Reconfigurable(${inner.desc})"
  def instantiate()(implicit p: Parameters): AbstractPrefetcher =
    Module(new ReconfigurablePrefetcher(inner)(p))
}

/** Wrap every configured TL prefetcher. Compose this to the left of the
  * ordinary barf.With*Prefetcher fragment in a target configuration.
  */
class WithReconfigurablePrefetchers extends Config((site, here, up) => {
  case TLPrefetcherKey =>
    val upstream = up(TLPrefetcherKey)
    upstream.copy(prefetcher = DfxConfigHelpers.wrapInnerFactory[String, CanInstantiatePrefetcher](
      upstream.prefetcher,
      inner => ReconfigurablePrefetcherParams(inner)))
})
