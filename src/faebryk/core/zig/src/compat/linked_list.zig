const std = @import("std");

/// Generic DoublyLinkedList compatible with the pre-0.15 API.
/// This provides the old std.DoublyLinkedList(T) interface that was
/// de-generified in Zig 0.15.
pub fn DoublyLinkedList(comptime T: type) type {
    return struct {
        const Self = @This();

        first: ?*Node = null,
        last: ?*Node = null,

        pub const Node = struct {
            prev: ?*Node = null,
            next: ?*Node = null,
            data: T,
        };

        pub fn append(list: *Self, new_node: *Node) void {
            if (list.last) |last| {
                last.next = new_node;
                new_node.prev = last;
            } else {
                list.first = new_node;
            }
            new_node.next = null;
            list.last = new_node;
        }

        pub fn prepend(list: *Self, new_node: *Node) void {
            if (list.first) |first| {
                first.prev = new_node;
                new_node.next = first;
            } else {
                list.last = new_node;
            }
            new_node.prev = null;
            list.first = new_node;
        }

        pub fn insertBefore(list: *Self, existing_node: *Node, new_node: *Node) void {
            new_node.next = existing_node;
            if (existing_node.prev) |prev_node| {
                new_node.prev = prev_node;
                prev_node.next = new_node;
            } else {
                new_node.prev = null;
                list.first = new_node;
            }
            existing_node.prev = new_node;
        }

        pub fn insertAfter(list: *Self, existing_node: *Node, new_node: *Node) void {
            new_node.prev = existing_node;
            if (existing_node.next) |next_node| {
                new_node.next = next_node;
                next_node.prev = new_node;
            } else {
                new_node.next = null;
                list.last = new_node;
            }
            existing_node.next = new_node;
        }

        pub fn remove(list: *Self, node: *Node) void {
            if (node.prev) |prev| {
                prev.next = node.next;
            } else {
                list.first = node.next;
            }
            if (node.next) |next| {
                next.prev = node.prev;
            } else {
                list.last = node.prev;
            }
            node.prev = null;
            node.next = null;
        }

        pub fn pop(list: *Self) ?*Node {
            if (list.last) |last| {
                list.remove(last);
                return last;
            }
            return null;
        }

        pub fn popFirst(list: *Self) ?*Node {
            if (list.first) |first| {
                list.remove(first);
                return first;
            }
            return null;
        }

        pub fn len(list: Self) usize {
            var count: usize = 0;
            var it = list.first;
            while (it) |node| : (it = node.next) {
                count += 1;
            }
            return count;
        }

        pub fn concatByMoving(list1: *Self, list2: *Self) void {
            if (list2.first) |first| {
                if (list1.last) |last| {
                    last.next = first;
                    first.prev = last;
                } else {
                    list1.first = first;
                }
                list1.last = list2.last;
            }
            list2.first = null;
            list2.last = null;
        }
    };
}

test "basic append and iterate" {
    const List = DoublyLinkedList(i32);
    var list: List = .{};

    var node1 = List.Node{ .data = 1 };
    var node2 = List.Node{ .data = 2 };
    var node3 = List.Node{ .data = 3 };

    list.append(&node1);
    list.append(&node2);
    list.append(&node3);

    try std.testing.expectEqual(@as(usize, 3), list.len());

    var sum: i32 = 0;
    var it = list.first;
    while (it) |n| : (it = n.next) {
        sum += n.data;
    }
    try std.testing.expectEqual(@as(i32, 6), sum);
}

test "prepend" {
    const List = DoublyLinkedList(i32);
    var list: List = .{};

    var node1 = List.Node{ .data = 1 };
    var node2 = List.Node{ .data = 2 };

    list.prepend(&node1);
    list.prepend(&node2);

    try std.testing.expectEqual(@as(i32, 2), list.first.?.data);
    try std.testing.expectEqual(@as(i32, 1), list.last.?.data);
}

test "remove" {
    const List = DoublyLinkedList(i32);
    var list: List = .{};

    var node1 = List.Node{ .data = 1 };
    var node2 = List.Node{ .data = 2 };
    var node3 = List.Node{ .data = 3 };

    list.append(&node1);
    list.append(&node2);
    list.append(&node3);

    list.remove(&node2);

    try std.testing.expectEqual(@as(usize, 2), list.len());
    try std.testing.expectEqual(@as(i32, 1), list.first.?.data);
    try std.testing.expectEqual(@as(i32, 3), list.last.?.data);
}
