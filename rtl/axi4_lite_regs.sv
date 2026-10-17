module axi4_lite_regs (
    input  logic        aclk,
    input  logic        aresetn,

    input  logic [31:0] s_awaddr,
    input  logic        s_awvalid,
    output logic        s_awready,

    input  logic [31:0] s_wdata,
    input  logic [3:0]  s_wstrb,
    input  logic        s_wvalid,
    output logic        s_wready,

    output logic [1:0]  s_bresp,
    output logic        s_bvalid,
    input  logic        s_bready,

    input  logic [31:0] s_araddr,
    input  logic        s_arvalid,
    output logic        s_arready,

    output logic [31:0] s_rdata,
    output logic [1:0]  s_rresp,
    output logic        s_rvalid,
    input  logic        s_rready,

    output logic [31:0] src_addr,
    output logic [31:0] dst_addr,
    output logic [31:0] length,
    output logic        start_pulse,

    input  logic        busy,
    input  logic        done,
    input  logic        error,
    input  logic [31:0] words_done,
    input  logic [31:0] error_code,

    output logic        irq
);

    localparam logic [31:0] REG_CONTROL    = 32'h00;
    localparam logic [31:0] REG_STATUS     = 32'h04;
    localparam logic [31:0] REG_SRC_ADDR   = 32'h08;
    localparam logic [31:0] REG_DST_ADDR   = 32'h0C;
    localparam logic [31:0] REG_LENGTH     = 32'h10;
    localparam logic [31:0] REG_WORDS_DONE = 32'h14;
    localparam logic [31:0] REG_IRQ_ENABLE = 32'h18;
    localparam logic [31:0] REG_IRQ_STATUS = 32'h1C;
    localparam logic [31:0] REG_ERROR_CODE = 32'h20;

    logic [31:0] irq_enable;
    logic [1:0]  irq_status;

    logic        aw_pending;
    logic [31:0] awaddr_saved;
    logic        w_pending;
    logic [31:0] wdata_saved;
    logic [3:0]  wstrb_saved;

    logic [31:0] write_addr;
    logic [31:0] write_data;
    logic [3:0]  write_strb;
    logic        write_fire;
    logic        aw_handshake;
    logic        w_handshake;

`ifdef FORMAL
    logic formal_past_valid = 1'b0;

    always_ff @(posedge aclk) begin
        formal_past_valid <= 1'b1;

        if (formal_past_valid && $past(aresetn) && aresetn) begin
            if (!$past(write_fire && write_addr == REG_SRC_ADDR))
                assert ($stable(src_addr));

            if (!$past(write_fire && write_addr == REG_DST_ADDR))
                assert ($stable(dst_addr));

            if (!$past(write_fire && write_addr == REG_LENGTH))
                assert ($stable(length));
        end
    end
`endif

    function automatic logic [31:0] apply_strb(
        input logic [31:0] old_value,
        input logic [31:0] new_value,
        input logic [3:0]  strb
    );
        logic [31:0] result;
        integer i;
        begin
            result = old_value;
            for (i = 0; i < 4; i = i + 1)
                if (strb[i])
                    result[i*8 +: 8] = new_value[i*8 +: 8];
            apply_strb = result;
        end
    endfunction

    assign s_awready = !aw_pending && !s_bvalid;
    assign s_wready  = !w_pending  && !s_bvalid;
    assign s_arready = !s_rvalid;

    assign aw_handshake = s_awvalid && s_awready;
    assign w_handshake  = s_wvalid  && s_wready;

    assign write_addr = aw_pending ? awaddr_saved : s_awaddr;
    assign write_data = w_pending  ? wdata_saved  : s_wdata;
    assign write_strb = w_pending  ? wstrb_saved  : s_wstrb;

    assign write_fire =
        !s_bvalid &&
        (aw_pending || aw_handshake) &&
        (w_pending  || w_handshake);

    always_ff @(posedge aclk) begin
        if (!aresetn) begin
            src_addr     <= 32'b0;
            dst_addr     <= 32'b0;
            length       <= 32'b0;
            irq_enable   <= 32'b0;
            irq_status   <= 2'b0;
            start_pulse  <= 1'b0;

            aw_pending   <= 1'b0;
            awaddr_saved <= 32'b0;
            w_pending    <= 1'b0;
            wdata_saved  <= 32'b0;
            wstrb_saved  <= 4'b0;

            s_bvalid <= 1'b0;
            s_bresp  <= 2'b00;
            s_rvalid <= 1'b0;
            s_rdata  <= 32'b0;
            s_rresp  <= 2'b00;
        end else begin
            start_pulse <= 1'b0;

            if (s_bvalid && s_bready)
                s_bvalid <= 1'b0;

            if (s_rvalid && s_rready)
                s_rvalid <= 1'b0;

            if (aw_handshake) begin
                aw_pending   <= 1'b1;
                awaddr_saved <= s_awaddr;
            end

            if (w_handshake) begin
                w_pending  <= 1'b1;
                wdata_saved <= s_wdata;
                wstrb_saved <= s_wstrb;
            end

            if (write_fire) begin
                aw_pending <= 1'b0;
                w_pending  <= 1'b0;
                s_bvalid   <= 1'b1;
                s_bresp    <= 2'b00;

                case (write_addr)
                    REG_CONTROL: begin
                        if (write_strb[0] && write_data[0] && !busy)
                            start_pulse <= 1'b1;
                    end

                    REG_SRC_ADDR:
                        src_addr <= apply_strb(src_addr, write_data, write_strb);

                    REG_DST_ADDR:
                        dst_addr <= apply_strb(dst_addr, write_data, write_strb);

                    REG_LENGTH:
                        length <= apply_strb(length, write_data, write_strb);

                    REG_IRQ_ENABLE:
                        irq_enable <= apply_strb(irq_enable, write_data, write_strb);

                    REG_IRQ_STATUS: begin
                        if (write_strb[0]) begin
                            if (write_data[0]) irq_status[0] <= 1'b0;
                            if (write_data[1]) irq_status[1] <= 1'b0;
                        end
                    end

                    default: s_bresp <= 2'b10;
                endcase
            end

            if (done)
                irq_status[0] <= 1'b1;
            if (error)
                irq_status[1] <= 1'b1;

            if (s_arvalid && s_arready) begin
                s_rvalid <= 1'b1;
                s_rresp  <= 2'b00;

                case (s_araddr)
                    REG_CONTROL:    s_rdata <= 32'b0;
                    REG_STATUS:     s_rdata <= {29'b0, error, done, busy};
                    REG_SRC_ADDR:   s_rdata <= src_addr;
                    REG_DST_ADDR:   s_rdata <= dst_addr;
                    REG_LENGTH:     s_rdata <= length;
                    REG_WORDS_DONE: s_rdata <= words_done;
                    REG_IRQ_ENABLE: s_rdata <= irq_enable;
                    REG_IRQ_STATUS: s_rdata <= {30'b0, irq_status};
                    REG_ERROR_CODE: s_rdata <= error_code;
                    default: begin
                        s_rdata <= 32'b0;
                        s_rresp <= 2'b10;
                    end
                endcase
            end
        end
    end

    assign irq = |(irq_enable[1:0] & irq_status);

endmodule
