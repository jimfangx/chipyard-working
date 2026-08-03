package chipyard.sky130.util.analog

import chisel3._
import chisel3.experimental.{Analog, attach}
import chisel3.util.HasBlackBoxInline

class AnalogDriver(width: Int) extends BlackBox with HasBlackBoxInline {
  val io = IO(new Bundle {
    val ana = Analog(width.W)
    val in = Input(Bits(width.W))
  })

  setInline("AnalogDriver.v",
    s"""
      |module AnalogDriver(
      |  inout [${width - 1}:0] ana,
      |  input [${width - 1}:0] in
      |);
      |  assign ana = in;
      |endmodule
      |""".stripMargin)
}

class AnalogReader(width: Int) extends BlackBox with HasBlackBoxInline {
  val io = IO(new Bundle {
    val ana = Analog(width.W)
    val out = Output(Bits(width.W))
  })

  setInline("AnalogReader.v",
    s"""
       |module AnalogReader(
       |  inout [${width - 1}:0] ana,
       |  output [${width - 1}:0] out
       |);
       |  assign out = ana;
       |endmodule
       |""".stripMargin)
}

object ConvertAnalog {
  def readFrom(ana: Analog): Bits = {
    val reader = Module(new AnalogReader(ana.getWidth))
    attach(ana, reader.io.ana)
    reader.io.out
  }

  def driveFrom(in: Bits): Analog = {
    val driver = Module(new AnalogDriver(in.getWidth))
    driver.io.in := in
    driver.io.ana
  }

  def drive(ana: Analog, from: Bits): Unit = {
    require(ana.getWidth == from.getWidth)

    val driver = Module(new AnalogDriver(ana.getWidth))

    driver.io.in := from
    attach(driver.io.ana, ana)
  }
}
