using System.Net;
using System.Net.Sockets;
using System.Text;

// very early proof-of-concept; just ensures we can read UDP send from the Pico W

const int PORT = 62212;
using UdpClient udpClient = new();
udpClient.Client.Bind(new IPEndPoint(IPAddress.Any, PORT));

_ = Task.Run(() => RunClientAsync());

Console.WriteLine("Receiving...");
while (true)
{
    IPEndPoint? from = null;
    var recvBuffer = udpClient.Receive(ref from);
    Console.WriteLine($"{Encoding.UTF8.GetString(recvBuffer)} from {from}");
}

static async Task RunClientAsync()
{
    await Task.Delay(5000);
    using Socket s = new(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
    var ep = new IPEndPoint(IPAddress.Parse("192.168.68.86"), PORT);
    Console.WriteLine("Sending...");
    while (true)
    {
        s.SendTo(Encoding.ASCII.GetBytes("From .NET"), ep);
        await Task.Delay(5000);
    }
}
