package chipyard.sky130

import chipyard.harness.BuildTop
import chipyard.iobinders.{HasIOBinders, IOCellKey}
import chipyard.iocell.{
  AnalogIOCell,
  AnalogIOCellBundle,
  DigitalGPIOCell,
  DigitalGPIOCellBundle,
  DigitalInIOCell,
  DigitalInIOCellBundle,
  DigitalOutIOCell,
  DigitalOutIOCellBundle,
  IOCell,
  IOCellTypeParams
}
import chipyard.sky130.util.analog.ConvertAnalog
import chisel3._
import chisel3.experimental.{Analog, BaseModule, attach}
import chisel3.util.HasBlackBoxResource
import freechips.rocketchip.util.ElaborationArtefacts
import org.chipsalliance.cde.config.{Config, Parameters}
import org.chipsalliance.diplomacy.lazymodule.{InModuleBody, LazyModule, ModuleValue}

import scala.collection.mutable

object consts {
  val defaultGPIOCellName = "sky130_ef_io__gpiov2_pad_wrapped"
  val defaultAnalogCellName = "sky130_ef_io__analog_pad"
  val defaultXRes4V2CellName = "sky130_fd_io__top_xres4v2"
}

class Sky130EFGPIOV2IO extends Bundle {
  // VCCHIB domain
  val OUT = Input(Bool())
  val OE_N = Input(Bool())

  // VCCD domain
  val SLOW = Input(Bool())
  val DM = Input(UInt(3.W))
  val VTRIP_SEL = Input(Bool())
  val INP_DIS = Input(Bool())
  val HLD_OVR = Input(Bool())
  val ENABLE_VDDIO = Input(Bool())
  val IB_MODE_SEL = Input(Bool())
  val ANALOG_EN = Input(Bool())
  val ANALOG_SEL = Input(Bool())
  val ANALOG_POL = Input(Bool())

  val HLD_H_N = Input(Bool())
  val ENABLE_H = Input(Bool())
  val ENABLE_INP_H = Input(Bool())
  val ENABLE_VDDA_H = Input(Bool())
  val ENABLE_VSWITCH_H = Input(Bool())

  val PAD = Analog(1.W)

  // Direct pad connections - VDDIO domain
  val PAD_A_NOESD_H = Analog(1.W)
  val PAD_A_ESD_0_H = Analog(1.W)
  val PAD_A_ESD_1_H = Analog(1.W)
  val AMUXBUS_A = Analog(1.W)
  val AMUXBUS_B = Analog(1.W)

  // VCCHIB domain
  val IN = Output(Bool())
  // VDDIO domain
  val IN_H = Output(Bool())

  // special nets used to tie off certain pins (ENABLE_INP_H)
  // VDDIO domain
  val TIE_HI_ESD = Output(Bool())
  val TIE_LO_ESD = Output(Bool())
}

class Sky130EFGPIOV2Cell(cellName: String = consts.defaultGPIOCellName, sim: Boolean) extends BlackBox with HasBlackBoxResource {
  val io = IO(new Sky130EFGPIOV2IO)

  override val desiredName = cellName

  if (sim) {
    addResource("/vsrc/sky130_iocells/sky130_ef_io__gpiov2_pad_wrapped.v")
    addResource("/vsrc/sky130_iocells/sky130_fd_io.v")
  }
}

class Sky130FDXRes4V2IO extends Bundle {
  val PAD = Analog(1.W)

  // VDDIO domain?
  val XRES_H_N = Output(Bool())
  val DISABLE_PULLUP_H = Input(Bool())
  val ENABLE_H = Input(Bool())
  val EN_VDDIO_SIG_H = Input(Bool())
  val INP_SEL_H = Input(Bool())
  val FILT_IN_H = Input(Bool())
  val PULLUP_H = Analog(1.W)

  // VCCD domain?
  val ENABLE_VDDIO = Input(Bool())

  // Direct pad connections - VDDIO domain
  val PAD_A_ESD_H = Analog(1.W)
  val AMUXBUS_A = Analog(1.W)
  val AMUXBUS_B = Analog(1.W)

  // special nets used to tie off certain pins (ENABLE_INP_H)
  // VDDIO domain
  val TIE_HI_ESD = Output(Bool())
  val TIE_LO_ESD = Output(Bool())
  val TIE_WEAK_HI_H = Analog(1.W)
}

class Sky130FDXRes4V2Cell(cellName: String = consts.defaultXRes4V2CellName, sim: Boolean)
  extends BlackBox with HasBlackBoxResource {
  val io = IO(new Sky130FDXRes4V2IO)

  override val desiredName = cellName

  if (sim) {
    addResource("/vsrc/sky130_iocells/sky130_fd_io.v")
  }
}

class Sky130EFAnalogCellIO extends Bundle {
  val P_PAD = Analog(1.W)
  val P_CORE = Analog(1.W)
  val AMUXBUS_A = Analog(1.W)
  val AMUXBUS_B = Analog(1.W)
}

class Sky130EFAnalogCell(cellName: String, sim: Boolean = false) extends BlackBox with HasBlackBoxResource {
  val io = IO(new Sky130EFAnalogCellIO)

  override val desiredName = cellName

  if (sim) {
    addResource("/vsrc/sky130_iocells/sky130_ef_io.v")
  }
}

class Sky130EFIOCellCommonIO extends Bundle {
  // VDDIO domain
  val porb_h = Input(Bool())
  val AMUXBUS_A = Analog(1.W)
  val AMUXBUS_B = Analog(1.W)
}

trait Sky130EFIOCellLike extends IOCell {
  this: BaseModule =>
  val iocell: BaseModule

  val commonIO = IO(new Sky130EFIOCellCommonIO)
}

abstract class Sky130EFGPIOV2CellIOCellBase(cellName: String, sim: Boolean = false) extends RawModule with Sky130EFIOCellLike {
  override val iocell = Module(new Sky130EFGPIOV2Cell(cellName = cellName, sim = sim))

  // special nets
  iocell.io.ENABLE_INP_H := iocell.io.TIE_LO_ESD // tie - disable input when enable_h low

  // VDDIO domain
  iocell.io.HLD_H_N := iocell.io.TIE_HI_ESD // stay out of hibernate/hold mode

  // VCCD (core) domain
  iocell.io.SLOW := false.B // no slow mode
  iocell.io.HLD_OVR := false.B // turn off overide
  iocell.io.VTRIP_SEL := false.B // CMOS input signalling not LVTTL
  iocell.io.IB_MODE_SEL := false.B // use VDDIO not VCCHIB for pad input signalling
  // FIXME: how to handle? see ENABLE_H
  // enable_vddio=1 implies VCCHIB + HV supplies valid, VCCD (+ LV) control signals valid
  // caravel ties to nearby VCCD supply
  iocell.io.ENABLE_VDDIO := true.B // enable HV circuits
  iocell.io.ANALOG_EN := false.B // disable analog driver
  iocell.io.ANALOG_SEL := false.B // tie off analog AMUXBUS sel for good measure
  iocell.io.ANALOG_POL := false.B // tie off analog polarity sel for good measure

  // VDDA domain
  iocell.io.ENABLE_VDDA_H := iocell.io.TIE_LO_ESD // disable analog supplies to analog block

  // VSWITCH domain
  iocell.io.ENABLE_VSWITCH_H := iocell.io.TIE_LO_ESD // disable pumped-up VDDA supply


  // VDDIO domain
  iocell.io.ENABLE_H := commonIO.porb_h

  attach(iocell.io.AMUXBUS_A, commonIO.AMUXBUS_A)
  attach(iocell.io.AMUXBUS_B, commonIO.AMUXBUS_B)
}

class Sky130EFGPIOV2CellAnalog(cellName: String = consts.defaultGPIOCellName)
  extends Sky130EFGPIOV2CellIOCellBase(cellName) with AnalogIOCell {
  val io = IO(new AnalogIOCellBundle)

  // FIXME: replace with analog pad cell

  attach(io.pad, iocell.io.PAD)
  attach(io.core, iocell.io.PAD_A_NOESD_H)
  // FIXME: what even should happen here...
  iocell.io.DM := "b000".U(3.W)
  iocell.io.OUT := false.B
  iocell.io.OE_N := true.B
  iocell.io.INP_DIS := true.B
}

class Sky130EFGPIOV2CellIO(cellName: String = consts.defaultGPIOCellName, sim: Boolean = false)
  extends Sky130EFGPIOV2CellIOCellBase(cellName, sim = sim) with DigitalGPIOCell {
  val io = IO(new DigitalGPIOCellBundle)

  attach(io.pad, iocell.io.PAD)

  iocell.io.DM := "b110".U(3.W)
  iocell.io.OUT := io.o
  iocell.io.OE_N := !io.oe
  io.i := iocell.io.IN
  iocell.io.INP_DIS := !io.ie
}

class Sky130EFGPIOV2CellIn(cellName: String = consts.defaultGPIOCellName, sim: Boolean = false)
  extends Sky130EFGPIOV2CellIOCellBase(cellName, sim = sim) with DigitalInIOCell {
  val io = IO(new DigitalInIOCellBundle)

  ConvertAnalog.drive(iocell.io.PAD, from = io.pad)

  iocell.io.DM := "b001".U(3.W)
  iocell.io.OUT := false.B
  iocell.io.OE_N := true.B
  io.i := iocell.io.IN
  iocell.io.INP_DIS := !io.ie
}

class Sky130EFGPIOV2CellOut(cellName: String = consts.defaultGPIOCellName, sim: Boolean = false)
  extends Sky130EFGPIOV2CellIOCellBase(cellName, sim = sim) with DigitalOutIOCell {
  val io = IO(new DigitalOutIOCellBundle)

  io.pad := ConvertAnalog.readFrom(iocell.io.PAD)

  iocell.io.DM := "b110".U(3.W)
  iocell.io.OUT := io.o
  iocell.io.OE_N := !io.oe
  iocell.io.INP_DIS := true.B
}

class Sky130EFGPIOV2CellNoConn(cellName: String = consts.defaultGPIOCellName, sim: Boolean = false)
  extends Sky130EFGPIOV2CellIOCellBase(cellName, sim = sim) with IOCell {
  val io = IO(new Bundle {
    val pad = Analog(1.W)
  })

  attach(io.pad, iocell.io.PAD)

  iocell.io.DM := "b000".U(3.W)
  iocell.io.OUT := false.B
  iocell.io.OE_N := true.B
  iocell.io.INP_DIS := true.B
}

class Sky130FDXRes4V2IOCell(cellName: String = consts.defaultXRes4V2CellName, sim: Boolean = false)
  extends RawModule with Sky130EFIOCellLike with DigitalInIOCell {
  override val iocell = Module(new Sky130FDXRes4V2Cell(cellName = cellName, sim = sim))

  val io = IO(new DigitalInIOCellBundle)

  ConvertAnalog.drive(iocell.io.PAD, from = io.pad)

  // reference: https://github.com/efabless/caravel/blob/5f4a5b7b46f05d476622ab9d9c24eb5721ef495a/verilog/rtl/chip_io.v#L306

  // VDDIO domain
  iocell.io.ENABLE_H := commonIO.porb_h
  attach(iocell.io.AMUXBUS_A, commonIO.AMUXBUS_A)
  attach(iocell.io.AMUXBUS_B, commonIO.AMUXBUS_B)
  attach(iocell.io.PAD_A_ESD_H, iocell.io.TIE_WEAK_HI_H) // weak pull-up connection

  iocell.io.DISABLE_PULLUP_H := iocell.io.TIE_LO_ESD // enable pull-up on reset pad
  iocell.io.EN_VDDIO_SIG_H := iocell.io.TIE_LO_ESD // "No idea."
  iocell.io.INP_SEL_H := iocell.io.TIE_LO_ESD // use pad input not filt_in_h
  iocell.io.FILT_IN_H := iocell.io.TIE_LO_ESD // alternate glitch filter input
  ConvertAnalog.drive(iocell.io.PULLUP_H, from = iocell.io.TIE_LO_ESD) // pullup connection for alternate glitch filter input

  // VCCD domain
  iocell.io.ENABLE_VDDIO := true.B // enable HV circuits?

  val levelShifter = Module(new Sky130FDLevelShifter(Sky130FDLevelShifters.defaults.hv2lv, sim))
  levelShifter.in := iocell.io.XRES_H_N
  io.i := !levelShifter.out
}

class Sky130EFAnalogCellIOCell(cellName: String, sim: Boolean = false)
  extends RawModule with Sky130EFIOCellLike with AnalogIOCell {
  override val iocell = Module(new Sky130EFAnalogCell(cellName = cellName, sim = sim))

  val io = IO(new AnalogIOCellBundle)

  attach(io.pad, iocell.io.P_PAD)
  attach(io.core, iocell.io.P_CORE)
  attach(iocell.io.AMUXBUS_A, commonIO.AMUXBUS_A)
  attach(iocell.io.AMUXBUS_B, commonIO.AMUXBUS_B)
}

case class Sky130EFIOCellTypeParams(
  gpioCellName: String = consts.defaultGPIOCellName,
  analogCellName: String = consts.defaultAnalogCellName,
  resetCellName: String = consts.defaultXRes4V2CellName,
  sim: Boolean = false
) extends IOCellTypeParams {
  override def analog() = Module(new Sky130EFAnalogCellIOCell(cellName = analogCellName, sim = sim))

  override def gpio() = Module(new Sky130EFGPIOV2CellIO(cellName = gpioCellName, sim = sim))

  override def input() = Module(new Sky130EFGPIOV2CellIn(cellName = gpioCellName, sim = sim))

  override def output() = Module(new Sky130EFGPIOV2CellOut(cellName = gpioCellName, sim = sim))

  override def inputForBit(name: Option[String], index: Int): DigitalInIOCell = name match {
    case Some("iocell_reset") => Module(new Sky130FDXRes4V2IOCell(cellName = resetCellName, sim = sim))
    case _ => input()
  }
}

/**
 * Use Sky130 gpiov2 IO cells
 *
 * This fragment also selects [[Sky130ChipTop]], which connects the process-specific
 * shared controls and emits `sky130io.json`. The digital system itself remains selected
 * by the rest of the Chipyard configuration, so this works with any standard core and
 * peripheral combination.
 *
 * @param cellName name of gpiov2 cell to instantiate
 */
class WithSky130EFIOCells(cellName: String = consts.defaultGPIOCellName, sim: Boolean = false)
  extends Config((site, here, up) => {
    case IOCellKey => Sky130EFIOCellTypeParams(gpioCellName = cellName, sim = sim)
    case BuildTop => (p: Parameters) => new Sky130ChipTop()(p)
  })

trait HasSky130EFIOCells {
  this: LazyModule with HasSky130EFCaravelPOR with HasIOBinders =>

  val sky130EFIOCellInsts: mutable.Buffer[Sky130EFIOCellLike] = mutable.Buffer[Sky130EFIOCellLike]()

  val AMUXBUS: ModuleValue[Option[(Analog, Analog)]] = InModuleBody {
    iocells.getWrappedValue.collectFirst {
      case cell: Sky130EFIOCellLike => (cell.commonIO.AMUXBUS_A, cell.commonIO.AMUXBUS_B)
    }
  }

  def registerSky130EFIOCell(cell: Sky130EFIOCellLike): Unit = {
    cell.commonIO.porb_h := porb_h.getWrappedValue
    AMUXBUS.getWrappedValue.foreach { case (amuxbus_a, amuxbus_b) =>
      attach(cell.commonIO.AMUXBUS_A, amuxbus_a)
      attach(cell.commonIO.AMUXBUS_B, amuxbus_b)
    }

    sky130EFIOCellInsts.append(cell)
  }

  InModuleBody {
    iocells.getWrappedValue.foreach {
      case cell: Sky130EFIOCellLike => registerSky130EFIOCell(cell)
      case cell =>
        throw new IllegalArgumentException(
          s"Sky130 IO cells were requested, but ${cell.getClass.getName} was generated. " +
          "All IO binders must use IOCellKey."
        )
    }
  }

  ElaborationArtefacts.add("sky130io.json", {
    "[\n" + sky130EFIOCellInsts.map { cell =>
      // instanceName includes Chisel's uniquifying suffix for each bit of a wide signal.
      val name = s"\"${escapeJson(cell.instanceName)}\""
      s"  {\n    \"name\": $name\n  }"
    }.mkString(",\n") + "\n]"
  })

  private def escapeJson(value: String): String = value.flatMap {
    case '"'  => "\\\""
    case '\\' => "\\\\"
    case '\b' => "\\b"
    case '\f' => "\\f"
    case '\n' => "\\n"
    case '\r' => "\\r"
    case '\t' => "\\t"
    case c if c.isControl => f"\\u${c.toInt}%04x"
    case c => c.toString
  }
}
