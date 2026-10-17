module axi4_lite_regs_formal (
    input logic aclk
);

    (* anyseq *) logic aresetn;
    (* anyseq *) logic [31:0] s_awaddr;
    (* anyseq *) logic s_awvalid;
    (* anyseq *) logic [31:0] s_wdata;
    (* anyseq *) logic [3:0] s_wstrb;
    (* anyseq *) logic s_wvalid;
    (* anyseq *) logic s_bready;
    (* anyseq *) logic [31:0] s_araddr;
    (* anyseq *) logic s_arvalid;
    (* anyseq *) logic s_rready;
    (* anyseq *) logic busy;
    (* anyseq *) logic done;
    (* anyseq *) logic error;
    (* anyseq *) logic [31:0] words_done;
    (* anyseq *) logic [31:0] error_code;

    wire s_awready, s_wready, s_bvalid;
    wire [1:0] s_bresp;
    wire s_arready, s_rvalid;
    wire [31:0] s_rdata;
    wire [1:0] s_rresp;
    wire [31:0] src_addr, dst_addr, length;
    wire start_pulse, irq;


    axi4_lite_regs dut (
        .aclk(aclk),
        .aresetn(aresetn),
        .s_awaddr(s_awaddr),
        .s_awvalid(s_awvalid),
        .s_awready(s_awready),
        .s_wdata(s_wdata),
        .s_wstrb(s_wstrb),
        .s_wvalid(s_wvalid),
        .s_wready(s_wready),
        .s_bresp(s_bresp),
        .s_bvalid(s_bvalid),
        .s_bready(s_bready),
        .s_araddr(s_araddr),
        .s_arvalid(s_arvalid),
        .s_arready(s_arready),
        .s_rdata(s_rdata),
        .s_rresp(s_rresp),
        .s_rvalid(s_rvalid),
        .s_rready(s_rready),
        .src_addr(src_addr),
        .dst_addr(dst_addr),
        .length(length),
        .start_pulse(start_pulse),
        .busy(busy),
        .done(done),
        .error(error),
        .words_done(words_done),
        .error_code(error_code),
        .irq(irq)
    );

    logic past_valid = 1'b0;

    always_ff @(posedge aclk) begin
        past_valid <= 1'b1;

        // Require reset on the first formal clock edge.
        if (!past_valid)
            assume (!aresetn);

        // After a sampled reset edge, resettable outputs must be clear.
        if (past_valid && !$past(aresetn)) begin
            assert (src_addr == 0);
            assert (dst_addr == 0);
            assert (length == 0);
            assert (start_pulse == 0);
            assert (s_bvalid == 0);
            assert (s_rvalid == 0);
            assert (irq == 0);
        end

        // AXI write response must remain valid and stable under backpressure.
        if (past_valid && $past(aresetn) && aresetn &&
            $past(s_bvalid && !s_bready)) begin
            assert (s_bvalid);
            assert ($stable(s_bresp));
        end

        // AXI read response must remain valid and stable under backpressure.
        if (past_valid && $past(aresetn) && aresetn &&
            $past(s_rvalid && !s_rready)) begin
            assert (s_rvalid);
            assert ($stable(s_rdata));
            assert ($stable(s_rresp));
        end


    end

endmodule
