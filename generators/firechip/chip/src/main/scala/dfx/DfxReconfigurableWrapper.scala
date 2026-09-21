package firechip.dfx

import chisel3._

/**
  * Marker for a FireSim Dynamic Function eXchange (DFX) partition boundary.
  *
  * A concrete wrapper must retain a stable emitted name, expose a fixed IO
  * interface across all reconfigurable-module variants, and instantiate its
  * implementation unconditionally as a sub-Module.  Those properties give
  * Vivado a stable cell to mark HD.RECONFIGURABLE while allowing the inner
  * implementation to vary between base and RM builds.
  */
trait DfxReconfigurableWrapper { this: Module =>
  /** Variant-invariant Verilog module name used to find the partition cell. */
  def wrapperName: String

  override def desiredName: String = wrapperName
}

/** Helpers for CDE fragments which replace an optional module factory with a
  * DFX wrapper around each configured implementation.
  */
object DfxConfigHelpers {
  def wrapInnerFactory[K, T](
    factory: K => Option[T],
    wrap: T => T
  ): K => Option[T] = (key: K) => factory(key).map(wrap)
}
