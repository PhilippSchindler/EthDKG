pragma solidity ^0.5.8;
pragma experimental ABIEncoderV2;

contract Testing {

    event SomethingHappend(uint256 x);

    struct PointG1 {
        uint256 x;
        uint256 y;
    }

    function test_addr_cast(uint256 addr) public view {
        require(
            uint256(msg.sender) == addr,
            "cast failed or endianness invalid"
        );
    }

    function do_something_with_points(PointG1[2] memory points)
    public pure
    {
        require(points.length > 1, "at least 2 point required");
        assert(points[0].x == 1);
        assert(points[0].y == 2);
        assert(points[1].x == 3);
        assert(points[1].y == 4);

        // abi.encodePacked(points); not supported (even in experminatal mode)
    }

    function do_something_with_uint256_tuples(uint256[2][] memory points)
    public pure
    {
        require(points.length > 1, "at least 2 point required");
        assert(points[0][0] == 1);
        assert(points[0][1] == 2);
        assert(points[1][0] == 3);
        assert(points[1][1] == 4);

        abi.encodePacked(points);
    }

    uint[2] public some_point;
    function set_some_point(uint256[2] memory value) public {
        some_point = value;
    }

    function trigger_something(uint256 x)
    public
    {
        emit SomethingHappend(x);
    }
}