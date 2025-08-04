const std = @import("std");
const tokenizer = @import("tokenizer.zig");

pub const Token = tokenizer.Token;
pub const TokenType = tokenizer.TokenType;

const LineInfo = struct {
    start: usize,
    end: usize,
    line_num: usize,
};

const WorkerResult = struct {
    tokens: []Token,
    token_count: usize,
};

const WorkerContext = struct {
    file_data: []const u8,
    lines: []const LineInfo,
    allocator: std.mem.Allocator,
    result: ?WorkerResult = null,
    err: ?anyerror = null,
};

fn tokenizeWorker(context: *WorkerContext) void {
    // Pre-allocate based on rough estimate (20 tokens per line)
    const estimated_tokens = context.lines.len * 20;
    var tokens = context.allocator.alloc(Token, estimated_tokens) catch |err| {
        context.err = err;
        return;
    };
    
    var token_count: usize = 0;
    
    // Process assigned lines
    for (context.lines) |line_info| {
        const line_data = context.file_data[line_info.start..line_info.end];
        
        // Create a tokenizer for this line
        var line_tokenizer = tokenizer.Tokenizer.init(context.allocator, line_data);
        
        // Tokenize the line
        while (line_tokenizer.nextToken() catch |err| {
            context.err = err;
            context.allocator.free(tokens);
            return;
        }) |token| {
            if (token_count >= tokens.len) {
                // Resize if needed
                const new_size = tokens.len * 2;
                const new_tokens = context.allocator.realloc(tokens, new_size) catch |err| {
                    context.err = err;
                    context.allocator.free(tokens);
                    return;
                };
                tokens = new_tokens;
            }
            
            // Adjust token position to be relative to the entire file
            var adjusted_token = token;
            adjusted_token.line = line_info.line_num;
            // Adjust the column if we track absolute positions
            
            tokens[token_count] = adjusted_token;
            token_count += 1;
        }
    }
    
    // Shrink to actual size
    if (token_count < tokens.len) {
        tokens = context.allocator.realloc(tokens, token_count) catch tokens[0..token_count];
    }
    
    context.result = .{
        .tokens = tokens,
        .token_count = token_count,
    };
}

pub fn tokenizeFileParallel(allocator: std.mem.Allocator, path: []const u8) ![]Token {
    const file = try std.fs.cwd().openFile(path, .{});
    defer file.close();
    
    const file_size = try file.getEndPos();
    
    // For small files, use single-threaded
    if (file_size < 100_000) { // 100KB threshold
        return tokenizer.tokenizeFile(allocator, path);
    }
    
    // Memory map the file
    const mapped = try std.posix.mmap(
        null,
        file_size,
        std.posix.PROT.READ,
        .{ .TYPE = .PRIVATE },
        file.handle,
        0,
    );
    defer std.posix.munmap(mapped);
    
    const file_data = mapped[0..file_size];
    
    // First pass: find all line boundaries
    var lines = std.ArrayList(LineInfo).init(allocator);
    defer lines.deinit();
    
    var line_start: usize = 0;
    var line_num: usize = 1;
    
    for (file_data, 0..) |byte, i| {
        if (byte == '\n' or i == file_data.len - 1) {
            const line_end = if (byte == '\n') i else i + 1;
            if (line_end > line_start) {
                try lines.append(.{
                    .start = line_start,
                    .end = line_end,
                    .line_num = line_num,
                });
            }
            line_start = i + 1;
            line_num += 1;
        }
    }
    
    const total_lines = lines.items.len;
    if (total_lines == 0) {
        return try allocator.alloc(Token, 0);
    }
    
    // Determine number of threads
    const cpu_count = try std.Thread.getCpuCount();
    const min_lines_per_thread = 1000; // At least 1000 lines per thread
    const max_threads = @min(cpu_count, 16); // Cap at 16 threads
    const thread_count = @min(max_threads, @max(1, total_lines / min_lines_per_thread));
    
    if (thread_count == 1) {
        return tokenizer.tokenizeFile(allocator, path);
    }
    
    // Divide work among threads
    var contexts = try allocator.alloc(WorkerContext, thread_count);
    defer allocator.free(contexts);
    
    const lines_per_thread = total_lines / thread_count;
    var current_line: usize = 0;
    
    for (0..thread_count) |i| {
        const start_line = current_line;
        const end_line = if (i == thread_count - 1) total_lines else current_line + lines_per_thread;
        
        contexts[i] = .{
            .file_data = file_data,
            .lines = lines.items[start_line..end_line],
            .allocator = allocator,
        };
        
        current_line = end_line;
    }
    
    // Create and run threads
    var threads = try allocator.alloc(std.Thread, thread_count);
    defer allocator.free(threads);
    
    for (0..thread_count) |i| {
        threads[i] = try std.Thread.spawn(.{}, tokenizeWorker, .{&contexts[i]});
    }
    
    // Wait for completion
    for (threads) |thread| {
        thread.join();
    }
    
    // Check for errors and count total tokens
    var total_tokens: usize = 0;
    for (contexts) |context| {
        if (context.err) |err| {
            // Clean up allocated memory
            for (contexts) |ctx| {
                if (ctx.result) |result| {
                    allocator.free(result.tokens);
                }
            }
            return err;
        }
        total_tokens += context.result.?.token_count;
    }
    
    // Merge results
    var result = try allocator.alloc(Token, total_tokens);
    var offset: usize = 0;
    
    for (contexts) |context| {
        const worker_result = context.result.?;
        const tokens = worker_result.tokens[0..worker_result.token_count];
        @memcpy(result[offset..][0..tokens.len], tokens);
        offset += tokens.len;
        allocator.free(worker_result.tokens);
    }
    
    return result;
}